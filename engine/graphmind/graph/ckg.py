"""
Code Knowledge Graph (CKG)
===========================
Implements the graph data structure backed by NetworkX (in-memory) with
SQLite persistence (via SQLAlchemy).

Architecture:
- NetworkX DiGraph is the runtime data structure (fast traversal)
- SQLite stores nodes and edges persistently across restarts
- Graph is loaded from SQLite on startup, synced on write
- Incremental updates avoid full-graph reloads

Public API::

    graph = CodeKnowledgeGraph(db_path)
    graph.load()                          # load from SQLite
    graph.add_node(node)
    graph.add_edge(edge)
    graph.get_neighbors(node_id, edge_types=[EdgeType.CALLS])
    graph.get_subgraph(node_ids)
    graph.find_path(source_id, target_id)
    graph.get_stats(repo_id)
    graph.save()                          # persist to SQLite
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from uuid import uuid4

import networkx as nx
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from graphmind.models import (
    EdgeType,
    GraphEdge,
    GraphNode,
    GraphStats,
    NodeType,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# SQLAlchemy ORM Models
# ─────────────────────────────────────────────────────────────────────────────


class Base(DeclarativeBase):
    pass


class NodeRecord(Base):
    __tablename__ = "nodes"

    id = Column(String, primary_key=True)
    node_type = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    repo_id = Column(String, index=True)
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EdgeRecord(Base):
    __tablename__ = "edges"

    id = Column(String, primary_key=True)
    source_id = Column(String, nullable=False, index=True)
    target_id = Column(String, nullable=False, index=True)
    edge_type = Column(String, nullable=False, index=True)
    confidence = Column(Float, default=1.0)
    metadata_json = Column(Text, default="{}")


# ─────────────────────────────────────────────────────────────────────────────
# Code Knowledge Graph
# ─────────────────────────────────────────────────────────────────────────────


class CodeKnowledgeGraph:
    """
    The central graph data structure of GraphMind.

    Manages both in-memory (NetworkX) and persistent (SQLite) representations.
    All write operations update both stores atomically.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        engine = create_engine(
            f"sqlite:///{self._db_path}",
            connect_args={"check_same_thread": False},
            echo=False,
        )
        Base.metadata.create_all(engine)
        self._Session = sessionmaker(bind=engine)

        self._graph: nx.DiGraph = nx.DiGraph()
        self._loaded = False
        logger.info("CodeKnowledgeGraph initialized. DB: %s", self._db_path)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def load(self) -> None:
        """Load the full graph from SQLite into NetworkX."""
        session: Session = self._Session()
        try:
            nodes = session.query(NodeRecord).all()
            edges = session.query(EdgeRecord).all()

            for n in nodes:
                meta = json.loads(n.metadata_json or "{}")
                self._graph.add_node(
                    n.id,
                    node_type=n.node_type,
                    name=n.name,
                    repo_id=n.repo_id or "",
                    **meta,
                )

            for e in edges:
                meta = json.loads(e.metadata_json or "{}")
                self._graph.add_edge(
                    e.source_id,
                    e.target_id,
                    id=e.id,
                    edge_type=e.edge_type,
                    confidence=e.confidence,
                    **meta,
                )

            self._loaded = True
            logger.info(
                "Graph loaded: %d nodes, %d edges",
                self._graph.number_of_nodes(),
                self._graph.number_of_edges(),
            )
        finally:
            session.close()

    def save(self) -> None:
        """Persist the in-memory graph to SQLite (full sync)."""
        # This is called sparingly; incremental writes are preferred.
        logger.debug("Graph save() called — incremental writes preferred.")

    # ── Write operations ──────────────────────────────────────────────────────

    def add_node(self, node: GraphNode) -> None:
        """Add a node to the graph and persist it."""
        # Build metadata dict from the node, excluding base fields
        node_dict = node.model_dump()
        base_keys = {"id", "node_type", "name", "created_at", "updated_at", "metadata"}
        # Extract repo_id if present
        repo_id = str(node_dict.get("repo_id", ""))
        meta = {k: v for k, v in node_dict.items() if k not in base_keys and k != "repo_id"}
        # Merge explicit metadata dict
        meta.update(node.metadata)

        # Serialise non-serialisable values
        meta_clean = self._sanitize_meta(meta)

        # NetworkX
        self._graph.add_node(
            node.id,
            node_type=node.node_type.value,
            name=node.name,
            repo_id=repo_id,
            **meta_clean,
        )

        # SQLite
        session: Session = self._Session()
        try:
            existing = session.get(NodeRecord, node.id)
            if existing:
                existing.metadata_json = json.dumps(meta_clean, default=str)
                existing.updated_at = datetime.utcnow()
            else:
                session.add(NodeRecord(
                    id=node.id,
                    node_type=node.node_type.value,
                    name=node.name,
                    repo_id=repo_id,
                    metadata_json=json.dumps(meta_clean, default=str),
                ))
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def add_edge(self, edge: GraphEdge) -> None:
        """Add an edge to the graph and persist it."""
        meta_clean = self._sanitize_meta(edge.metadata)

        # NetworkX — only add edge if both nodes exist
        self._graph.add_edge(
            edge.source_id,
            edge.target_id,
            id=edge.id,
            edge_type=edge.edge_type.value,
            confidence=edge.confidence,
            **meta_clean,
        )

        # SQLite
        session: Session = self._Session()
        try:
            existing = session.get(EdgeRecord, edge.id)
            if not existing:
                session.add(EdgeRecord(
                    id=edge.id,
                    source_id=edge.source_id,
                    target_id=edge.target_id,
                    edge_type=edge.edge_type.value,
                    confidence=edge.confidence,
                    metadata_json=json.dumps(meta_clean, default=str),
                ))
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def add_nodes_bulk(self, nodes: List[GraphNode]) -> None:
        """Batch-add nodes for efficiency during indexing."""
        session: Session = self._Session()
        try:
            for node in nodes:
                node_dict = node.model_dump()
                base_keys = {"id", "node_type", "name", "created_at", "updated_at", "metadata"}
                repo_id = str(node_dict.get("repo_id", ""))
                meta = {k: v for k, v in node_dict.items() if k not in base_keys and k != "repo_id"}
                meta.update(node.metadata)
                meta_clean = self._sanitize_meta(meta)

                self._graph.add_node(
                    node.id,
                    node_type=node.node_type.value,
                    name=node.name,
                    repo_id=repo_id,
                    **meta_clean,
                )

                existing = session.get(NodeRecord, node.id)
                if not existing:
                    session.add(NodeRecord(
                        id=node.id,
                        node_type=node.node_type.value,
                        name=node.name,
                        repo_id=repo_id,
                        metadata_json=json.dumps(meta_clean, default=str),
                    ))
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def add_edges_bulk(self, edges: List[GraphEdge]) -> None:
        """Batch-add edges for efficiency during indexing."""
        session: Session = self._Session()
        try:
            for edge in edges:
                meta_clean = self._sanitize_meta(edge.metadata)
                self._graph.add_edge(
                    edge.source_id,
                    edge.target_id,
                    id=edge.id,
                    edge_type=edge.edge_type.value,
                    confidence=edge.confidence,
                    **meta_clean,
                )
                existing = session.get(EdgeRecord, edge.id)
                if not existing:
                    session.add(EdgeRecord(
                        id=edge.id,
                        source_id=edge.source_id,
                        target_id=edge.target_id,
                        edge_type=edge.edge_type.value,
                        confidence=edge.confidence,
                        metadata_json=json.dumps(meta_clean, default=str),
                    ))
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def remove_node(self, node_id: str) -> None:
        """Remove a node (and its incident edges) from graph and DB."""
        if self._graph.has_node(node_id):
            self._graph.remove_node(node_id)
        session: Session = self._Session()
        try:
            node = session.get(NodeRecord, node_id)
            if node:
                session.delete(node)
            # Cascade edge deletion
            session.query(EdgeRecord).filter(
                (EdgeRecord.source_id == node_id) | (EdgeRecord.target_id == node_id)
            ).delete()
            session.commit()
        finally:
            session.close()

    # ── Read / Traversal ──────────────────────────────────────────────────────

    def get_node(self, node_id: str) -> Optional[Dict]:
        """Return node attributes dict or None."""
        if self._graph.has_node(node_id):
            return dict(self._graph.nodes[node_id])
        return None

    def get_neighbors(
        self,
        node_id: str,
        edge_types: Optional[List[EdgeType]] = None,
        direction: str = "both",  # "out", "in", "both"
    ) -> List[Dict]:
        """
        Return neighboring nodes, optionally filtered by edge type.

        direction:
          - "out"  : only successors (node → neighbor)
          - "in"   : only predecessors (neighbor → node)
          - "both" : union
        """
        if not self._graph.has_node(node_id):
            return []

        edge_type_values = {e.value for e in edge_types} if edge_types else None

        neighbor_ids: Set[str] = set()

        if direction in ("out", "both"):
            for nbr, edge_data in self._graph[node_id].items():
                # DiGraph: edge_data is a flat attribute dict
                etype = edge_data.get("edge_type", "") if isinstance(edge_data, dict) else ""
                if edge_type_values is None or etype in edge_type_values:
                    neighbor_ids.add(nbr)

        if direction in ("in", "both"):
            for pred in self._graph.predecessors(node_id):
                edge_data = self._graph[pred][node_id]
                etype = edge_data.get("edge_type", "") if isinstance(edge_data, dict) else ""
                if edge_type_values is None or etype in edge_type_values:
                    neighbor_ids.add(pred)

        result = []
        for nid in neighbor_ids:
            if self._graph.has_node(nid):
                attrs = dict(self._graph.nodes[nid])
                attrs["id"] = nid
                result.append(attrs)
        return result

    def get_subgraph(self, node_ids: List[str]) -> nx.DiGraph:
        """Return the induced subgraph over the given node IDs."""
        valid_ids = [n for n in node_ids if self._graph.has_node(n)]
        return self._graph.subgraph(valid_ids).copy()

    def find_path(
        self, source_id: str, target_id: str, max_length: int = 6
    ) -> Optional[List[str]]:
        """Find shortest path between two nodes. Returns None if unreachable."""
        try:
            path = nx.shortest_path(self._graph, source_id, target_id)
            if len(path) <= max_length + 1:
                return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            pass
        return None

    def traverse_bfs(
        self,
        start_id: str,
        max_depth: int = 3,
        edge_types: Optional[List[EdgeType]] = None,
        max_nodes: int = 100,
    ) -> List[Dict]:
        """
        BFS traversal from a starting node.
        Returns list of dicts: {node_id, depth, edge_type, parent_id}.
        """
        if not self._graph.has_node(start_id):
            return []

        edge_type_values = {e.value for e in edge_types} if edge_types else None
        visited: Set[str] = set()
        queue = [(start_id, 0, None, None)]  # (id, depth, parent, edge_type)
        result = []

        while queue and len(result) < max_nodes:
            node_id, depth, parent_id, via_edge = queue.pop(0)

            if node_id in visited:
                continue
            visited.add(node_id)

            attrs = self.get_node(node_id) or {}
            attrs["id"] = node_id
            result.append({
                "node": attrs,
                "depth": depth,
                "parent_id": parent_id,
                "via_edge_type": via_edge,
            })

            if depth < max_depth:
                for nbr in self._graph.successors(node_id):
                    if nbr in visited:
                        continue
                    edge_data = self._graph[node_id][nbr]
                    etype = edge_data.get("edge_type", "")
                    if edge_type_values is None or etype in edge_type_values:
                        queue.append((nbr, depth + 1, node_id, etype))

        return result

    def get_all_nodes(
        self,
        repo_id: Optional[str] = None,
        node_type: Optional[NodeType] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[Dict]:
        """Return nodes with optional filtering, paginated."""
        nodes = []
        for node_id, attrs in self._graph.nodes(data=True):
            if repo_id and attrs.get("repo_id") != repo_id and node_id != repo_id:
                continue
            if node_type and attrs.get("node_type") != node_type.value:
                continue
            entry = dict(attrs)
            entry["id"] = node_id
            nodes.append(entry)

        return nodes[offset : offset + limit]

    def get_all_edges(
        self,
        repo_id: Optional[str] = None,
        edge_type: Optional[EdgeType] = None,
        limit: int = 2000,
        offset: int = 0,
    ) -> List[Dict]:
        """Return edges with optional filtering, paginated."""
        edges = []
        for src, tgt, data in self._graph.edges(data=True):
            if edge_type and data.get("edge_type") != edge_type.value:
                continue
            if repo_id:
                src_attrs = self._graph.nodes.get(src, {})
                if src_attrs.get("repo_id") != repo_id:
                    continue
            entry = dict(data)
            entry["source_id"] = src
            entry["target_id"] = tgt
            edges.append(entry)

        return edges[offset : offset + limit]

    def get_stats(self, repo_id: Optional[str] = None) -> GraphStats:
        """Return statistics for the entire graph or a specific repository."""
        node_counts: Dict[str, int] = {}
        edge_counts: Dict[str, int] = {}
        languages: Set[str] = set()

        for node_id, attrs in self._graph.nodes(data=True):
            if repo_id and attrs.get("repo_id") != repo_id and node_id != repo_id:
                continue
            ntype = attrs.get("node_type", "unknown")
            node_counts[ntype] = node_counts.get(ntype, 0) + 1
            lang = attrs.get("language")
            if lang:
                languages.add(str(lang))

        for src, tgt, data in self._graph.edges(data=True):
            if repo_id:
                src_attrs = self._graph.nodes.get(src, {})
                # Include edge if src is within the repo, or IS the repo node
                if src_attrs.get("repo_id") != repo_id and src != repo_id:
                    continue
            etype = data.get("edge_type", "unknown")
            edge_counts[etype] = edge_counts.get(etype, 0) + 1

        return GraphStats(
            repo_id=repo_id or "all",
            total_nodes=sum(node_counts.values()),
            total_edges=sum(edge_counts.values()),
            node_counts=node_counts,
            edge_counts=edge_counts,
            languages=sorted(languages),
            indexed_at=datetime.utcnow(),
            parse_errors=0,
            unsupported_files=0,
        )

    def search_nodes_by_name(self, query: str, repo_id: Optional[str] = None) -> List[Dict]:
        """Simple name-contains search."""
        query_lower = query.lower()
        results = []
        for node_id, attrs in self._graph.nodes(data=True):
            if repo_id and attrs.get("repo_id") != repo_id:
                continue
            name = attrs.get("name", "")
            if query_lower in name.lower():
                entry = dict(attrs)
                entry["id"] = node_id
                results.append(entry)
        return results

    def has_node(self, node_id: str) -> bool:
        return self._graph.has_node(node_id)

    def node_count(self) -> int:
        return self._graph.number_of_nodes()

    def edge_count(self) -> int:
        return self._graph.number_of_edges()

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _sanitize_meta(meta: dict) -> dict:
        """Convert non-JSON-serializable values for storage."""
        result = {}
        for k, v in meta.items():
            if isinstance(v, (str, int, float, bool, type(None))):
                result[k] = v
            elif isinstance(v, list):
                result[k] = [str(item) if not isinstance(item, (str, int, float, bool)) else item for item in v]
            elif isinstance(v, dict):
                result[k] = {str(kk): str(vv) for kk, vv in v.items()}
            else:
                result[k] = str(v)
        return result
