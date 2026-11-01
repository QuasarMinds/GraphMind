"""
Repository Scanner
===================
Recursively walks a repository, detects file languages, extracts
basic file metadata, and feeds files to the parsing pipeline.

Design principles:
- Pure generator-based walk (memory-efficient for huge repos)
- Configurable ignore rules (dirs, extensions, size limits)
- Returns FileInfo objects; parsing is NOT done here
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator, List, Optional, Set

import chardet

from graphmind.config import EngineSettings, settings
from graphmind.models import Language, ParseStatus, compute_hash

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Language detection table (extension → Language)
# ─────────────────────────────────────────────────────────────────────────────

_EXT_TO_LANG: dict[str, Language] = {
    ".py": Language.PYTHON,
    ".pyi": Language.PYTHON,
    ".js": Language.JAVASCRIPT,
    ".mjs": Language.JAVASCRIPT,
    ".cjs": Language.JAVASCRIPT,
    ".jsx": Language.JAVASCRIPT,
    ".ts": Language.TYPESCRIPT,
    ".tsx": Language.TYPESCRIPT,
    ".mts": Language.TYPESCRIPT,
}


@dataclass
class FileInfo:
    """Raw metadata for a file discovered during scanning."""

    absolute_path: Path
    relative_path: str          # relative to repo root
    language: Language
    size_bytes: int
    encoding: str
    content_hash: str
    line_count: int
    parse_status: ParseStatus   # set to PENDING or SKIPPED
    skip_reason: Optional[str] = None


@dataclass
class ScanResult:
    """Aggregated result of scanning an entire repository."""

    repo_path: Path
    files: List[FileInfo] = field(default_factory=list)
    skipped_files: int = 0
    total_dirs: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def language_stats(self) -> dict[str, int]:
        stats: dict[str, int] = {}
        for f in self.files:
            lang = f.language.value
            stats[lang] = stats.get(lang, 0) + 1
        return stats

    @property
    def parseable_files(self) -> List[FileInfo]:
        return [f for f in self.files if f.parse_status == ParseStatus.PENDING]


class RepositoryScanner:
    """
    Scans a repository directory and returns structured file metadata.

    Usage::

        scanner = RepositoryScanner(settings)
        result = scanner.scan("/path/to/repo")
        for file_info in result.parseable_files:
            print(file_info.relative_path, file_info.language)
    """

    def __init__(self, cfg: EngineSettings = settings) -> None:
        self._cfg = cfg
        self._excluded_dirs: Set[str] = set(cfg.excluded_dirs)
        self._excluded_exts: Set[str] = set(cfg.excluded_extensions)

    # ── Public ────────────────────────────────────────────────────────────────

    def scan(self, repo_path: str | Path) -> ScanResult:
        """Synchronously scan a repository. Returns a ScanResult."""
        repo_path = Path(repo_path).resolve()
        if not repo_path.exists():
            raise FileNotFoundError(f"Repository path does not exist: {repo_path}")
        if not repo_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {repo_path}")

        result = ScanResult(repo_path=repo_path)
        for file_info in self._walk(repo_path, result):
            result.files.append(file_info)

        logger.info(
            "Scan complete: %s — %d files (%d parseable, %d skipped)",
            repo_path,
            len(result.files),
            len(result.parseable_files),
            result.skipped_files,
        )
        return result

    def detect_language(self, path: Path) -> Language:
        """Return the Language for a file based on its extension."""
        return _EXT_TO_LANG.get(path.suffix.lower(), Language.UNKNOWN)

    # ── Private ───────────────────────────────────────────────────────────────

    def _walk(
        self, root: Path, result: ScanResult
    ) -> Generator[FileInfo, None, None]:
        """Depth-first generator over repository files."""
        try:
            entries = list(root.iterdir())
        except PermissionError as e:
            result.errors.append(f"Permission denied: {root}: {e}")
            return

        for entry in sorted(entries):
            if entry.is_symlink() and not self._cfg.follow_symlinks:
                continue

            if entry.is_dir():
                if entry.name in self._excluded_dirs or entry.name.startswith("."):
                    # Allow .git check but skip all hidden dirs and excluded dirs
                    # We explicitly keep .github, .vscode etc. names in excluded_dirs
                    if entry.name in self._excluded_dirs:
                        continue
                result.total_dirs += 1
                yield from self._walk(entry, result)

            elif entry.is_file():
                file_info = self._process_file(entry, root, result)
                if file_info:
                    yield file_info

    def _process_file(
        self, path: Path, repo_root: Path, result: ScanResult
    ) -> Optional[FileInfo]:
        """Process a single file and return FileInfo or None on hard skip."""
        try:
            rel_path = str(path.relative_to(repo_root)).replace(os.sep, "/")
            size_bytes = path.stat().st_size
            language = self.detect_language(path)

            # Skip binary/excluded extensions
            if path.suffix.lower() in self._excluded_exts:
                result.skipped_files += 1
                return None

            # Size check — index but mark as skipped for parsing
            max_bytes = self._cfg.max_file_size_kb * 1024
            if size_bytes > max_bytes:
                result.skipped_files += 1
                return FileInfo(
                    absolute_path=path,
                    relative_path=rel_path,
                    language=language,
                    size_bytes=size_bytes,
                    encoding="unknown",
                    content_hash="",
                    line_count=0,
                    parse_status=ParseStatus.SKIPPED,
                    skip_reason=f"File too large ({size_bytes} bytes > {max_bytes})",
                )

            # Read and hash
            raw = path.read_bytes()
            detected = chardet.detect(raw[:4096])
            encoding = detected.get("encoding") or "utf-8"
            try:
                text = raw.decode(encoding, errors="replace")
            except (LookupError, UnicodeDecodeError):
                text = raw.decode("utf-8", errors="replace")
                encoding = "utf-8"

            content_hash = compute_hash(text)
            line_count = text.count("\n") + 1

            # Mark as PENDING (parseable) or UNSUPPORTED
            if language == Language.UNKNOWN:
                parse_status = ParseStatus.UNSUPPORTED
            else:
                parse_status = ParseStatus.PENDING

            return FileInfo(
                absolute_path=path,
                relative_path=rel_path,
                language=language,
                size_bytes=size_bytes,
                encoding=encoding,
                content_hash=content_hash,
                line_count=line_count,
                parse_status=parse_status,
            )

        except OSError as e:
            logger.warning("Could not read file %s: %s", path, e)
            result.errors.append(f"Read error: {path}: {e}")
            return None
