"""
Tests: Code Knowledge Graph
"""

import tempfile
from pathlib import Path

import pytest

from graphmind.graph.ckg import CodeKnowledgeGraph
from graphmind.models import (
    ClassNode,
    EdgeType,
    FileNode,
    FunctionNode,
    GraphEdge,
    Language,
    NodeType,
    ParseStatus,
    RepositoryNode,
)


@pytest.fixture
def graph(tmp_path: Path) -> CodeKnowledgeGraph:
    g = CodeKnowledgeGraph(tmp_path / "test.db")
    g.load()
    return g


def make_repo(name: str = "test-repo") -> RepositoryNode:
    return RepositoryNode(id=f"repo-{name}", name=name, path=f"/path/to/{name}")


def make_file(repo_id: str, name: str = "main.py") -> FileNode:
    return FileNode(
        id=f"file-{name}",
        name=name,
        path=f"src/{name}",
        repo_id=repo_id,
        language=Language.PYTHON,
        parse_status=ParseStatus.PARSED,
    )


def make_class(file_id: str, repo_id: str, name: str = "MyClass") -> ClassNode:
    return ClassNode(id=f"cls-{name}", name=name, file_id=file_id, repo_id=repo_id)


def make_fn(file_id: str, repo_id: str, name: str = "my_fn") -> FunctionNode:
    return FunctionNode(id=f"fn-{name}", name=name, file_id=file_id, repo_id=repo_id)


def test_add_and_retrieve_node(graph: CodeKnowledgeGraph):
    repo = make_repo()
    graph.add_node(repo)
    assert graph.has_node(repo.id)
    attrs = graph.get_node(repo.id)
    assert attrs is not None
    assert attrs["name"] == "test-repo"


def test_add_edge(graph: CodeKnowledgeGraph):
    repo = make_repo()
    file = make_file(repo.id)
    graph.add_node(repo)
    graph.add_node(file)
    edge = GraphEdge(source_id=repo.id, target_id=file.id, edge_type=EdgeType.CONTAINS)
    graph.add_edge(edge)
    assert graph.edge_count() == 1


def test_get_neighbors(graph: CodeKnowledgeGraph):
    repo = make_repo()
    file = make_file(repo.id)
    graph.add_node(repo)
    graph.add_node(file)
    edge = GraphEdge(source_id=repo.id, target_id=file.id, edge_type=EdgeType.CONTAINS)
    graph.add_edge(edge)

    neighbors = graph.get_neighbors(repo.id, direction="out")
    assert any(n["name"] == "main.py" for n in neighbors)


def test_neighbor_filter_by_edge_type(graph: CodeKnowledgeGraph):
    repo = make_repo()
    f1 = make_file(repo.id, "a.py")
    f2 = make_file(repo.id, "b.py")
    graph.add_node(repo)
    graph.add_node(f1)
    graph.add_node(f2)
    graph.add_edge(GraphEdge(source_id=repo.id, target_id=f1.id, edge_type=EdgeType.CONTAINS))
    graph.add_edge(GraphEdge(source_id=repo.id, target_id=f2.id, edge_type=EdgeType.IMPORTS))

    # Filter for only CONTAINS
    nbrs = graph.get_neighbors(repo.id, edge_types=[EdgeType.CONTAINS], direction="out")
    names = [n["name"] for n in nbrs]
    assert "a.py" in names
    assert "b.py" not in names


def test_remove_node(graph: CodeKnowledgeGraph):
    repo = make_repo()
    file = make_file(repo.id)
    graph.add_node(repo)
    graph.add_node(file)
    graph.add_edge(GraphEdge(source_id=repo.id, target_id=file.id, edge_type=EdgeType.CONTAINS))
    graph.remove_node(file.id)
    assert not graph.has_node(file.id)


def test_bfs_traversal(graph: CodeKnowledgeGraph):
    repo = make_repo()
    file = make_file(repo.id)
    cls = make_class(file.id, repo.id)
    graph.add_node(repo)
    graph.add_node(file)
    graph.add_node(cls)
    graph.add_edge(GraphEdge(source_id=repo.id, target_id=file.id, edge_type=EdgeType.CONTAINS))
    graph.add_edge(GraphEdge(source_id=file.id, target_id=cls.id, edge_type=EdgeType.DEFINES))

    steps = graph.traverse_bfs(repo.id, max_depth=2)
    node_ids = [s["node"]["id"] for s in steps]
    assert repo.id in node_ids
    assert file.id in node_ids
    assert cls.id in node_ids


def test_graph_stats(graph: CodeKnowledgeGraph):
    repo = make_repo()
    file = make_file(repo.id)
    graph.add_node(repo)
    graph.add_node(file)
    graph.add_edge(GraphEdge(source_id=repo.id, target_id=file.id, edge_type=EdgeType.CONTAINS))

    stats = graph.get_stats(repo_id=repo.id)
    assert stats.total_nodes >= 2
    assert stats.total_edges >= 1


def test_persistence(tmp_path: Path):
    """Nodes written to one graph instance should survive in a new instance."""
    db = tmp_path / "persist.db"
    g1 = CodeKnowledgeGraph(db)
    g1.load()
    repo = make_repo("persistent")
    g1.add_node(repo)
    del g1

    g2 = CodeKnowledgeGraph(db)
    g2.load()
    assert g2.has_node(repo.id)
    attrs = g2.get_node(repo.id)
    assert attrs["name"] == "persistent"


def test_search_nodes_by_name(graph: CodeKnowledgeGraph):
    repo = make_repo()
    file = make_file(repo.id, "authentication.py")
    graph.add_node(repo)
    graph.add_node(file)

    results = graph.search_nodes_by_name("auth", repo_id=repo.id)
    names = [r["name"] for r in results]
    assert "authentication.py" in names
