"""
GraphMind — Shared Domain Models
==================================
Pydantic models used across the engine, API, and integration layers.
These are the canonical data structures for graph nodes, edges,
retrieval results, and context ledger entries.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field, computed_field


# ─────────────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────────────


class NodeType(str, Enum):
    REPOSITORY = "repository"
    DIRECTORY = "directory"
    FILE = "file"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    IMPORT = "import"
    INTERFACE = "interface"
    MODULE = "module"


class EdgeType(str, Enum):
    CONTAINS = "CONTAINS"
    IMPORTS = "IMPORTS"
    CALLS = "CALLS"
    INHERITS = "INHERITS"
    IMPLEMENTS = "IMPLEMENTS"
    DEFINES = "DEFINES"
    USES = "USES"
    DEPENDS_ON = "DEPENDS_ON"


class ParseStatus(str, Enum):
    PENDING = "pending"
    PARSED = "parsed"
    FAILED = "failed"
    SKIPPED = "skipped"
    UNSUPPORTED = "unsupported"


class RepresentationLevel(int, Enum):
    UNLOADED = 0
    SIGNATURE = 1
    SUMMARY = 2
    FULL = 3


class ContextStatus(str, Enum):
    ACTIVE = "active"
    COMPRESSED = "compressed"
    INVALIDATED = "invalidated"
    EVICTED = "evicted"


class Language(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    UNKNOWN = "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# Graph Nodes
# ─────────────────────────────────────────────────────────────────────────────


class GraphNode(BaseModel):
    """Base class for all graph nodes."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    node_type: NodeType
    name: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class RepositoryNode(GraphNode):
    node_type: NodeType = NodeType.REPOSITORY
    path: str
    language_stats: Dict[str, int] = Field(default_factory=dict)
    indexed_at: Optional[datetime] = None
    total_files: int = 0
    parsed_files: int = 0


class DirectoryNode(GraphNode):
    node_type: NodeType = NodeType.DIRECTORY
    path: str
    repo_id: str
    parent_id: Optional[str] = None
    file_count: int = 0


class FileNode(GraphNode):
    node_type: NodeType = NodeType.FILE
    path: str
    repo_id: str
    language: Language = Language.UNKNOWN
    size_bytes: int = 0
    content_hash: str = ""
    parse_status: ParseStatus = ParseStatus.PENDING
    symbol_count: int = 0
    line_count: int = 0
    encoding: str = "utf-8"


class ClassNode(GraphNode):
    node_type: NodeType = NodeType.CLASS
    file_id: str
    repo_id: str
    start_line: int = 0
    end_line: int = 0
    bases: List[str] = Field(default_factory=list)
    docstring: Optional[str] = None
    is_abstract: bool = False


class FunctionNode(GraphNode):
    node_type: NodeType = NodeType.FUNCTION
    file_id: str
    repo_id: str
    start_line: int = 0
    end_line: int = 0
    params: List[Dict[str, str]] = Field(default_factory=list)
    return_type: Optional[str] = None
    docstring: Optional[str] = None
    is_async: bool = False
    decorators: List[str] = Field(default_factory=list)
    content_hash: str = ""


class MethodNode(GraphNode):
    node_type: NodeType = NodeType.METHOD
    file_id: str
    class_id: str
    repo_id: str
    start_line: int = 0
    end_line: int = 0
    params: List[Dict[str, str]] = Field(default_factory=list)
    return_type: Optional[str] = None
    docstring: Optional[str] = None
    is_async: bool = False
    is_static: bool = False
    is_class_method: bool = False
    decorators: List[str] = Field(default_factory=list)


class ImportNode(GraphNode):
    node_type: NodeType = NodeType.IMPORT
    file_id: str
    repo_id: str
    module: str
    alias: Optional[str] = None
    imported_names: List[str] = Field(default_factory=list)
    line: int = 0
    is_relative: bool = False


class VariableNode(GraphNode):
    node_type: NodeType = NodeType.VARIABLE
    file_id: str
    repo_id: str
    scope_id: Optional[str] = None  # function/class/module
    type_annotation: Optional[str] = None
    line: int = 0
    is_constant: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# Graph Edges
# ─────────────────────────────────────────────────────────────────────────────


class GraphEdge(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    source_id: str
    target_id: str
    edge_type: EdgeType
    confidence: float = 1.0  # 0.0–1.0; <1.0 means uncertain (e.g., dynamic call)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Retrieval
# ─────────────────────────────────────────────────────────────────────────────


class RetrievalResult(BaseModel):
    node_id: str
    node_type: NodeType
    name: str
    file_path: str
    start_line: int = 0
    end_line: int = 0
    score: float = 0.0
    keyword_score: float = 0.0
    semantic_score: float = 0.0
    symbol_score: float = 0.0
    graph_score: float = 0.0
    snippet: Optional[str] = None
    reason: str = ""


class RetrievalQuery(BaseModel):
    query: str
    repo_id: str
    top_k: int = 20
    methods: List[str] = Field(default=["keyword", "semantic", "symbol", "graph"])
    keyword_weight: float = 0.25
    semantic_weight: float = 0.35
    symbol_weight: float = 0.20
    graph_weight: float = 0.20
    token_budget: Optional[int] = None


# ─────────────────────────────────────────────────────────────────────────────
# Context Manager
# ─────────────────────────────────────────────────────────────────────────────


class LedgerEntry(BaseModel):
    """A single entry in the Context Ledger."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    entity_id: str
    file_path: str
    symbol_name: Optional[str] = None
    content_hash: str
    version: int = 1
    first_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    representation_level: RepresentationLevel = RepresentationLevel.UNLOADED
    related_entities: List[str] = Field(default_factory=list)
    status: ContextStatus = ContextStatus.ACTIVE
    transmitted: bool = False         # actually sent in current session
    token_estimate: int = 0
    session_id: Optional[str] = None

    @computed_field
    @property
    def is_stale(self) -> bool:
        return self.status in (ContextStatus.INVALIDATED, ContextStatus.EVICTED)


class ContextBundle(BaseModel):
    """The assembled context returned to an agent or external consumer."""

    session_id: str
    query: str
    entries: List[LedgerEntry]
    total_token_estimate: int
    budget_used_pct: float
    deduplication_savings: int  # tokens saved by not re-sending known content
    compression_savings: int    # tokens saved by sending summaries instead of full


class GraphStats(BaseModel):
    """High-level statistics about a repository's code knowledge graph."""

    repo_id: str
    total_nodes: int
    total_edges: int
    node_counts: Dict[str, int]  # NodeType → count
    edge_counts: Dict[str, int]  # EdgeType → count
    languages: List[str]
    indexed_at: Optional[datetime]
    parse_errors: int
    unsupported_files: int


# ─────────────────────────────────────────────────────────────────────────────
# Utility
# ─────────────────────────────────────────────────────────────────────────────


def compute_hash(content: str) -> str:
    """Stable SHA-256 hash of file/symbol content."""
    return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()


def estimate_tokens(text: str) -> int:
    """Heuristic token count (character ÷ 4). Replaced by tiktoken when available."""
    return max(1, len(text) // 4)
