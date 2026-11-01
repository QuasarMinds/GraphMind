"""
Tests: Repository Scanner
"""

import tempfile
from pathlib import Path

import pytest

from graphmind.scanner.scanner import RepositoryScanner
from graphmind.config import EngineSettings
from graphmind.models import Language, ParseStatus


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    """Create a minimal fake Python/JS repo for testing."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("def hello(): pass\n")
    (tmp_path / "src" / "utils.py").write_text("import os\n\nclass Util: pass\n")
    (tmp_path / "src" / "app.js").write_text("function main() { return 1; }\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "lodash.js").write_text("// should be excluded")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    (tmp_path / "README.md").write_text("# Test repo\n")
    return tmp_path


def make_scanner() -> RepositoryScanner:
    return RepositoryScanner(EngineSettings())


def test_scanner_finds_python_files(sample_repo: Path):
    scanner = make_scanner()
    result = scanner.scan(sample_repo)
    py_files = [f for f in result.files if f.language == Language.PYTHON]
    assert len(py_files) == 2, f"Expected 2 Python files, found {len(py_files)}"


def test_scanner_finds_js_files(sample_repo: Path):
    scanner = make_scanner()
    result = scanner.scan(sample_repo)
    js_files = [f for f in result.files if f.language == Language.JAVASCRIPT]
    assert len(js_files) == 1


def test_scanner_excludes_node_modules(sample_repo: Path):
    scanner = make_scanner()
    result = scanner.scan(sample_repo)
    paths = [f.relative_path for f in result.files]
    assert not any("node_modules" in p for p in paths)


def test_scanner_excludes_git(sample_repo: Path):
    scanner = make_scanner()
    result = scanner.scan(sample_repo)
    paths = [f.relative_path for f in result.files]
    assert not any(".git" in p for p in paths)


def test_scanner_marks_pending_parseable(sample_repo: Path):
    scanner = make_scanner()
    result = scanner.scan(sample_repo)
    for f in result.parseable_files:
        assert f.parse_status == ParseStatus.PENDING


def test_scanner_language_stats(sample_repo: Path):
    scanner = make_scanner()
    result = scanner.scan(sample_repo)
    stats = result.language_stats
    assert stats.get("python", 0) == 2
    assert stats.get("javascript", 0) == 1


def test_scanner_missing_path():
    scanner = make_scanner()
    with pytest.raises(FileNotFoundError):
        scanner.scan("/nonexistent/path/12345")


def test_scanner_file_hashes(sample_repo: Path):
    scanner = make_scanner()
    result = scanner.scan(sample_repo)
    hashes = [f.content_hash for f in result.parseable_files if f.content_hash]
    # All hashes should be unique (different files have different content)
    assert len(hashes) == len(set(hashes))
