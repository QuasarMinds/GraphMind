"""
GraphMind Engine Configuration
================================
Centralizes all engine settings. Uses pydantic-settings so values can
be overridden via environment variables (GRAPHMIND_*) or a config file.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EngineSettings(BaseSettings):
    """All tunable settings for the GraphMind engine."""

    model_config = SettingsConfigDict(
        env_prefix="GRAPHMIND_",
        env_file=".env",
        extra="ignore",
    )

    # ── Storage ──────────────────────────────────────────────────────────────
    data_dir: Path = Field(
        default=Path.home() / ".graphmind",
        description="Root directory for all persisted data.",
    )

    @property
    def db_path(self) -> Path:
        return self.data_dir / "graphmind.db"

    @property
    def embeddings_dir(self) -> Path:
        return self.data_dir / "embeddings"

    # ── Scanner ───────────────────────────────────────────────────────────────
    excluded_dirs: List[str] = Field(
        default=[
            ".git", ".hg", ".svn",
            "node_modules", "__pycache__", ".pytest_cache",
            "venv", ".venv", "env", ".env",
            "dist", "build", "target", "out", ".next", ".nuxt",
            "vendor", "third_party",
            ".mypy_cache", ".ruff_cache", ".tox",
        ],
        description="Directory names to skip during scanning.",
    )
    excluded_extensions: List[str] = Field(
        default=[
            # Binaries
            ".pyc", ".pyo", ".pyd", ".so", ".dll", ".dylib", ".exe", ".bin",
            # Images / media
            ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
            ".mp4", ".mp3", ".wav", ".avi",
            # Archives
            ".zip", ".tar", ".gz", ".bz2", ".rar", ".7z",
            # Compiled / generated
            ".min.js", ".min.css", ".map",
            # Data
            ".pkl", ".pickle", ".npy", ".npz", ".parquet",
            # Lock files (still scanned but not parsed)
        ],
        description="File extensions to skip entirely.",
    )
    max_file_size_kb: int = Field(
        default=512,
        description="Files larger than this are skipped during parsing (but indexed).",
    )
    follow_symlinks: bool = False

    # ── Parsing ───────────────────────────────────────────────────────────────
    supported_languages: List[str] = Field(default=["python", "javascript", "typescript"])
    parse_timeout_seconds: float = 10.0

    # ── Graph ─────────────────────────────────────────────────────────────────
    max_graph_nodes: int = 500_000
    graph_auto_persist: bool = True
    graph_persist_interval_s: int = 300  # 5 minutes

    # ── Retrieval ─────────────────────────────────────────────────────────────
    retrieval_top_k: int = 20
    keyword_weight: float = 0.25
    semantic_weight: float = 0.35
    symbol_weight: float = 0.20
    graph_weight: float = 0.20
    semantic_model: str = "all-MiniLM-L6-v2"
    embedding_batch_size: int = 64
    graph_traversal_depth: int = 3

    # ── Context Manager ───────────────────────────────────────────────────────
    default_token_budget: int = 16_000
    eviction_threshold: float = 0.85   # start evicting at 85% budget
    compression_threshold: float = 0.70

    # ── API ───────────────────────────────────────────────────────────────────
    api_host: str = "127.0.0.1"
    api_port: int = 7430
    api_cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = "INFO"
    log_file: Optional[Path] = None

    @field_validator("data_dir", mode="before")
    @classmethod
    def expand_path(cls, v: str | Path) -> Path:
        return Path(v).expanduser().resolve()

    def ensure_dirs(self) -> None:
        """Create all required data directories."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)


# Module-level singleton — import this wherever settings are needed.
settings = EngineSettings()
