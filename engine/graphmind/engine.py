"""
GraphMind Engine — Main Orchestrator
======================================
The GraphMindEngine class is the primary entry point for the engine.
It coordinates all subsystems: scanner, parser, extraction, graph, retrieval,
and context management.

External consumers (CLI agent, API, external tools) should use this class
rather than calling subsystems directly.

Usage::

    engine = GraphMindEngine()
    repo = engine.index_repository("/path/to/repo")
    results = engine.retrieve("authentication logic", repo_id=repo.id)
    context = engine.get_context("auth flow", repo_id=repo.id, budget=8000)
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from graphmind.config import EngineSettings, settings
from graphmind.extraction.extractor import SymbolExtractor
from graphmind.graph.ckg import CodeKnowledgeGraph
from graphmind.models import (
    DirectoryNode,
    FileNode,
    GraphStats,
    Language,
    NodeType,
    ParseStatus,
    RepositoryNode,
    compute_hash,
)
from graphmind.parser.parser import SourceParser
from graphmind.scanner.scanner import FileInfo, RepositoryScanner, ScanResult

logger = logging.getLogger(__name__)


class IndexingProgress:
    """Tracks progress of a repository indexing operation."""

    def __init__(self, total_files: int, repo_id: str) -> None:
        self.repo_id = repo_id
        self.total_files = total_files
        self.processed = 0
        self.parsed = 0
        self.failed = 0
        self.skipped = 0
        self.started_at = time.time()
        self.finished_at: Optional[float] = None
        self.current_file: str = ""
        self.errors: List[str] = []

    @property
    def pct(self) -> float:
        if self.total_files == 0:
            return 100.0
        return (self.processed / self.total_files) * 100.0

    @property
    def elapsed_s(self) -> float:
        end = self.finished_at or time.time()
        return end - self.started_at

    @property
    def is_complete(self) -> bool:
        return self.finished_at is not None

    def to_dict(self) -> dict:
        return {
            "repo_id": self.repo_id,
            "total_files": self.total_files,
            "processed": self.processed,
            "parsed": self.parsed,
            "failed": self.failed,
            "skipped": self.skipped,
            "pct": round(self.pct, 1),
            "elapsed_s": round(self.elapsed_s, 2),
            "current_file": self.current_file,
            "is_complete": self.is_complete,
            "errors": self.errors[:20],
        }


class GraphMindEngine:
    """
    Top-level engine coordinator.

    Maintains a single CodeKnowledgeGraph shared across all indexed
    repositories. Each repository gets its own RepositoryNode with a
    unique ID used to partition queries.
    """

    def __init__(self, cfg: EngineSettings = settings) -> None:
        self._cfg = cfg
        self._cfg.ensure_dirs()

        self._scanner = RepositoryScanner(cfg)
        self._parser = SourceParser(timeout_seconds=cfg.parse_timeout_seconds)
        self._extractor = SymbolExtractor()
        self._graph = CodeKnowledgeGraph(cfg.db_path)
        self._graph.load()

        # Active indexing tasks: repo_id → IndexingProgress
        self._indexing: Dict[str, IndexingProgress] = {}

        # Repository registry: path → repo_id
        self._repo_registry: Dict[str, str] = {}
        self._restore_repo_registry()

        logger.info("GraphMindEngine ready. Graph: %d nodes.", self._graph.node_count())

    # ── Repository Management ─────────────────────────────────────────────────

    def index_repository(
        self,
        repo_path: str | Path,
        force_reindex: bool = False,
    ) -> RepositoryNode:
        """
        Scan, parse, and index a repository.
        Returns the RepositoryNode. May raise on I/O errors.
        """
        repo_path = Path(repo_path).resolve()
        path_str = str(repo_path)

        # Check if already indexed
        existing_repo_id = self._repo_registry.get(path_str)
        if existing_repo_id and not force_reindex:
            existing = self._graph.get_node(existing_repo_id)
            if existing:
                logger.info("Repository already indexed: %s", path_str)
                return RepositoryNode(
                    id=existing_repo_id,
                    name=repo_path.name,
                    path=path_str,
                )

        # Scan
        logger.info("Scanning repository: %s", repo_path)
        scan_result: ScanResult = self._scanner.scan(repo_path)

        parseable = scan_result.parseable_files
        repo_id = existing_repo_id or str(uuid4())

        # Create progress tracker
        progress = IndexingProgress(total_files=len(parseable), repo_id=repo_id)
        self._indexing[repo_id] = progress

        # Build RepositoryNode
        repo_node = RepositoryNode(
            id=repo_id,
            name=repo_path.name,
            path=path_str,
            total_files=len(scan_result.files),
            language_stats=scan_result.language_stats,
        )
        self._graph.add_node(repo_node)
        self._repo_registry[path_str] = repo_id

        # Index directories
        self._index_directories(scan_result, repo_id, repo_path)

        # Index files — parse and extract symbols
        all_nodes = []
        all_edges = []

        for file_info in parseable:
            progress.current_file = file_info.relative_path
            # Skip files whose content hasn't changed (incremental reindex)
            if not force_reindex and not self._needs_reindex(file_info, repo_id):
                progress.processed += 1
                progress.skipped += 1
                continue
            file_node, nodes, edges = self._index_file(file_info, repo_id, repo_path)
            all_nodes.extend(nodes)
            all_edges.extend(edges)
            progress.processed += 1
            progress.parsed += 1

        # Also add skipped files
        for file_info in scan_result.files:
            if file_info.parse_status in (ParseStatus.SKIPPED, ParseStatus.UNSUPPORTED):
                file_node = self._make_file_node(file_info, repo_id)
                all_nodes.append(file_node)
                progress.skipped += 1

        # Bulk write
        if all_nodes:
            self._graph.add_nodes_bulk(all_nodes)
        if all_edges:
            self._graph.add_edges_bulk(all_edges)

        progress.finished_at = time.time()
        logger.info(
            "Indexing complete: %s — %d parsed, %d skipped, %.1fs",
            repo_path.name,
            progress.parsed,
            progress.skipped,
            progress.elapsed_s,
        )

        return repo_node

    def get_repository(self, repo_id: str) -> Optional[Dict]:
        """Return the repository node attributes."""
        return self._graph.get_node(repo_id)

    def list_repositories(self) -> List[Dict]:
        """Return all indexed repositories."""
        return self._graph.get_all_nodes(node_type=NodeType.REPOSITORY, limit=1000)

    def get_indexing_progress(self, repo_id: str) -> Optional[Dict]:
        prog = self._indexing.get(repo_id)
        return prog.to_dict() if prog else None

    # ── Graph Access ──────────────────────────────────────────────────────────

    @property
    def graph(self) -> CodeKnowledgeGraph:
        """Direct access to the Code Knowledge Graph."""
        return self._graph

    def get_stats(self, repo_id: Optional[str] = None) -> GraphStats:
        return self._graph.get_stats(repo_id)

    # ── Retrieval (stub — Phase 4 will implement fully) ───────────────────────

    def retrieve(self, query: str, repo_id: str, top_k: int = 20) -> List[Dict]:
        """
        Keyword-only retrieval (Phase 1 stub).
        Returns nodes whose name contains the query terms.
        Full hybrid retrieval is implemented in Phase 4.
        """
        results = self._graph.search_nodes_by_name(query, repo_id=repo_id)
        return results[:top_k]

    # ── Private Helpers ───────────────────────────────────────────────────────

    def _needs_reindex(self, file_info: FileInfo, repo_id: str) -> bool:
        """Return True if this file is new or its content hash has changed."""
        file_id = compute_hash(f"{repo_id}::{file_info.relative_path}")
        existing = self._graph.get_node(file_id)
        if not existing:
            return True
        return existing.get("content_hash", "") != file_info.content_hash

    def _index_directories(
        self, scan_result: ScanResult, repo_id: str, repo_root: Path
    ) -> None:
        from graphmind.models import GraphEdge, EdgeType  # local import to avoid cycle
        seen_dirs: set = set()
        for file_info in scan_result.files:
            parts = Path(file_info.relative_path).parts
            for depth in range(len(parts) - 1):
                dir_rel = "/".join(parts[:depth + 1])
                if dir_rel in seen_dirs:
                    continue
                seen_dirs.add(dir_rel)
                dir_id = compute_hash(f"{repo_id}::{dir_rel}")
                parent_rel = "/".join(parts[:depth]) if depth > 0 else None
                parent_id = (
                    compute_hash(f"{repo_id}::{parent_rel}") if parent_rel else repo_id
                )

                dir_node = DirectoryNode(
                    id=dir_id,
                    name=parts[depth],
                    path=dir_rel,
                    repo_id=repo_id,
                    parent_id=parent_id,
                )
                self._graph.add_node(dir_node)
                # CONTAINS edge: parent (repo or dir) → this directory
                try:
                    self._graph.add_edge(
                        GraphEdge(
                            source_id=parent_id,
                            target_id=dir_id,
                            edge_type=EdgeType.CONTAINS,
                        )
                    )
                except Exception:
                    pass  # parent may not yet exist; bulk-add will not re-check

    def _index_file(
        self, file_info: FileInfo, repo_id: str, repo_root: Path
    ) -> tuple:
        """Parse a file and extract symbols. Returns (FileNode, nodes, edges)."""
        file_id = compute_hash(f"{repo_id}::{file_info.relative_path}")
        file_node = FileNode(
            id=file_id,
            name=file_info.absolute_path.name,
            path=file_info.relative_path,
            repo_id=repo_id,
            language=file_info.language,
            size_bytes=file_info.size_bytes,
            content_hash=file_info.content_hash,
            parse_status=file_info.parse_status,
            line_count=file_info.line_count,
            encoding=file_info.encoding,
        )

        nodes = [file_node]
        # CONTAINS edge: parent directory → file
        parts = file_info.relative_path.split("/")
        parent_dir_id = (
            compute_hash(f"{repo_id}::{'/'.join(parts[:-1])}")
            if len(parts) > 1
            else repo_id
        )
        from graphmind.models import GraphEdge, EdgeType as ET  # local import
        edges = [
            GraphEdge(
                source_id=parent_dir_id,
                target_id=file_id,
                edge_type=ET.CONTAINS,
            )
        ]

        if not self._parser.is_available():
            return file_node, nodes, edges

        # Parse
        parsed = self._parser.parse_file(
            file_info.absolute_path,
            file_info.language,
        )

        if not parsed.is_valid:
            file_node.parse_status = parsed.parse_status
            return file_node, nodes, edges

        file_node.parse_status = ParseStatus.PARSED

        # Extract symbols
        result = self._extractor.extract(parsed, file_node)
        nodes.extend(result.nodes)
        edges.extend(result.edges)
        file_node.symbol_count = len(result.nodes)

        return file_node, nodes, edges

    def _make_file_node(self, file_info: FileInfo, repo_id: str) -> FileNode:
        file_id = compute_hash(f"{repo_id}::{file_info.relative_path}")
        return FileNode(
            id=file_id,
            name=file_info.absolute_path.name,
            path=file_info.relative_path,
            repo_id=repo_id,
            language=file_info.language,
            size_bytes=file_info.size_bytes,
            content_hash=file_info.content_hash,
            parse_status=file_info.parse_status,
            line_count=file_info.line_count,
            encoding=file_info.encoding,
        )

    def _restore_repo_registry(self) -> None:
        """Rebuild the path→repo_id registry from the graph on startup."""
        repos = self._graph.get_all_nodes(node_type=NodeType.REPOSITORY)
        for r in repos:
            path = r.get("path")
            if path:
                self._repo_registry[path] = r["id"]
        logger.debug("Restored %d repositories from graph.", len(self._repo_registry))
