"""
Tests: GraphMindEngine integration  (Phase 2)
=============================================
End-to-end: scan → parse → extract → graph → API queries.
All tests use a temporary directory as both the data store and the sample repo.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from graphmind.config import EngineSettings
from graphmind.engine import GraphMindEngine
from graphmind.models import EdgeType, NodeType


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    """Minimal Python repo that exercises classes, methods, functions, imports."""
    src = tmp_path / "src"
    src.mkdir()

    (src / "models.py").write_text(
        """\
class User:
    \"\"\"Domain model for a user.\"\"\"

    def __init__(self, name: str) -> None:
        self.name = name

    def greet(self) -> str:
        return f"Hello, {self.name}"

    @staticmethod
    def anonymous() -> "User":
        return User("guest")
""",
        encoding="utf-8",
    )

    (src / "services.py").write_text(
        """\
from src.models import User

class UserService:
    def create_user(self, name: str) -> User:
        return User(name)

    def get_greeting(self, user: User) -> str:
        return user.greet()

MAX_USERS = 1000
""",
        encoding="utf-8",
    )

    (src / "utils.py").write_text(
        """\
import os
import json

def read_config(path: str) -> dict:
    with open(path) as f:
        return json.load(f)

def write_config(path: str, data: dict) -> None:
    with open(path, "w") as f:
        json.dump(data, f)

DEBUG = False
""",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def engine(tmp_path: Path, sample_repo: Path) -> GraphMindEngine:
    cfg = EngineSettings(data_dir=tmp_path / ".graphmind_test")
    return GraphMindEngine(cfg)


# ─────────────────────────────────────────────────────────────────────────────
# Repository-level tests
# ─────────────────────────────────────────────────────────────────────────────


def test_engine_indexes_repository(engine: GraphMindEngine, sample_repo: Path):
    repo = engine.index_repository(sample_repo)
    assert repo.id
    assert repo.name == sample_repo.name
    assert engine.graph.has_node(repo.id)


def test_engine_creates_file_nodes(engine: GraphMindEngine, sample_repo: Path):
    repo = engine.index_repository(sample_repo)
    nodes = engine.graph.get_all_nodes(repo_id=repo.id, node_type=NodeType.FILE)
    names = {n["name"] for n in nodes}
    assert "models.py" in names
    assert "services.py" in names
    assert "utils.py" in names


def test_engine_creates_class_nodes(engine: GraphMindEngine, sample_repo: Path):
    repo = engine.index_repository(sample_repo)
    nodes = engine.graph.get_all_nodes(repo_id=repo.id, node_type=NodeType.CLASS)
    names = {n["name"] for n in nodes}
    assert "User" in names
    assert "UserService" in names


def test_engine_creates_method_nodes(engine: GraphMindEngine, sample_repo: Path):
    repo = engine.index_repository(sample_repo)
    nodes = engine.graph.get_all_nodes(repo_id=repo.id, node_type=NodeType.METHOD)
    names = {n["name"] for n in nodes}
    assert "__init__" in names
    assert "greet" in names
    assert "create_user" in names


def test_engine_creates_function_nodes(engine: GraphMindEngine, sample_repo: Path):
    repo = engine.index_repository(sample_repo)
    nodes = engine.graph.get_all_nodes(repo_id=repo.id, node_type=NodeType.FUNCTION)
    names = {n["name"] for n in nodes}
    assert "read_config" in names
    assert "write_config" in names


def test_engine_creates_import_nodes(engine: GraphMindEngine, sample_repo: Path):
    repo = engine.index_repository(sample_repo)
    nodes = engine.graph.get_all_nodes(repo_id=repo.id, node_type=NodeType.IMPORT)
    names = {n["name"] for n in nodes}
    assert "os" in names
    assert "json" in names


def test_engine_graph_has_edges(engine: GraphMindEngine, sample_repo: Path):
    repo = engine.index_repository(sample_repo)
    stats = engine.get_stats(repo.id)
    assert stats.total_edges > 0


def test_engine_graph_stats_languages(engine: GraphMindEngine, sample_repo: Path):
    repo = engine.index_repository(sample_repo)
    stats = engine.get_stats(repo.id)
    assert "python" in stats.languages


def test_engine_graph_stats_node_counts(engine: GraphMindEngine, sample_repo: Path):
    repo = engine.index_repository(sample_repo)
    stats = engine.get_stats(repo.id)
    assert stats.node_counts.get("file", 0) >= 3
    assert stats.node_counts.get("class", 0) >= 2
    assert stats.node_counts.get("method", 0) >= 3


def test_engine_no_duplicate_repo_on_reindex(
    engine: GraphMindEngine, sample_repo: Path
):
    """Indexing the same repo twice without force should return the same ID."""
    repo1 = engine.index_repository(sample_repo)
    repo2 = engine.index_repository(sample_repo)
    assert repo1.id == repo2.id


def test_engine_force_reindex(engine: GraphMindEngine, sample_repo: Path):
    repo1 = engine.index_repository(sample_repo)
    repo2 = engine.index_repository(sample_repo, force_reindex=True)
    assert repo1.id == repo2.id  # ID is deterministic (based on path hash)


def test_engine_progress_tracking(engine: GraphMindEngine, sample_repo: Path):
    repo = engine.index_repository(sample_repo)
    prog = engine.get_indexing_progress(repo.id)
    assert prog is not None
    assert prog["is_complete"] is True
    assert prog["parsed"] >= 3


def test_engine_list_repositories(engine: GraphMindEngine, sample_repo: Path):
    engine.index_repository(sample_repo)
    repos = engine.list_repositories()
    assert len(repos) >= 1
    paths = [r.get("path") for r in repos]
    assert str(sample_repo) in paths


def test_engine_keyword_retrieval(engine: GraphMindEngine, sample_repo: Path):
    repo = engine.index_repository(sample_repo)
    results = engine.retrieve("User", repo_id=repo.id, top_k=10)
    names = {r.get("name") for r in results}
    assert "User" in names or "UserService" in names


def test_engine_bfs_traversal(engine: GraphMindEngine, sample_repo: Path):
    repo = engine.index_repository(sample_repo)
    steps = engine.graph.traverse_bfs(repo.id, max_depth=2, max_nodes=50)
    ids = {s["node"]["id"] for s in steps}
    assert repo.id in ids
    assert len(ids) > 1  # repo + some children


def test_engine_graph_persistence(tmp_path: Path, sample_repo: Path):
    """Nodes indexed in one engine instance must survive to a new instance."""
    cfg = EngineSettings(data_dir=tmp_path / ".gm_persist")
    e1 = GraphMindEngine(cfg)
    repo = e1.index_repository(sample_repo)
    del e1

    e2 = GraphMindEngine(cfg)
    assert e2.graph.has_node(repo.id)
    classes = e2.graph.get_all_nodes(repo_id=repo.id, node_type=NodeType.CLASS)
    names = {n["name"] for n in classes}
    assert "User" in names

