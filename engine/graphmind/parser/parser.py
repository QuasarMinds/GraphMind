"""
Tree-sitter Parser Layer
=========================
Wraps the tree-sitter library to produce ASTs for supported languages.

Architecture notes:
- Each language grammar is loaded once and cached.
- The parser is thread-safe when used with separate Parser instances.
- ParsedFile contains the raw AST and source text; symbol extraction
  happens in the extraction layer, not here.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

from graphmind.models import Language, ParseStatus

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Optional tree-sitter import — gracefully degrade if not installed
# ─────────────────────────────────────────────────────────────────────────────

try:
    import tree_sitter_python as tspython
    import tree_sitter_javascript as tsjavascript
    from tree_sitter import Language as TSLanguage, Parser as TSParser, Node as TSNode

    _PYTHON_LANG = TSLanguage(tspython.language())
    _JS_LANG = TSLanguage(tsjavascript.language())

    # TypeScript shares the JS grammar in tree-sitter-javascript
    _LANG_MAP: Dict[Language, TSLanguage] = {
        Language.PYTHON: _PYTHON_LANG,
        Language.JAVASCRIPT: _JS_LANG,
        Language.TYPESCRIPT: _JS_LANG,  # ts grammar via same package
    }
    _TREE_SITTER_AVAILABLE = True
    logger.debug("Tree-sitter loaded successfully.")

except ImportError as _e:
    logger.warning(
        "tree-sitter not available (%s). Parsing will be disabled. "
        "Install tree-sitter-python and tree-sitter-javascript.",
        _e,
    )
    _TREE_SITTER_AVAILABLE = False
    _LANG_MAP = {}
    TSNode = object  # type: ignore[assignment,misc]


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ParsedFile:
    """The output of parsing a single source file."""

    file_path: str
    language: Language
    source: str
    tree: object            # tree_sitter.Tree (or None if unavailable)
    root_node: object       # tree_sitter.Node (or None)
    parse_status: ParseStatus
    parse_time_ms: float = 0.0
    error_count: int = 0    # number of ERROR nodes in the AST
    error: Optional[str] = None

    @property
    def has_errors(self) -> bool:
        return self.error_count > 0 or self.error is not None

    @property
    def is_valid(self) -> bool:
        return self.parse_status == ParseStatus.PARSED


# ─────────────────────────────────────────────────────────────────────────────
# Parser
# ─────────────────────────────────────────────────────────────────────────────


class SourceParser:
    """
    Parses source files into tree-sitter ASTs.

    Usage::

        parser = SourceParser()
        parsed = parser.parse_file(file_info)
        if parsed.is_valid:
            walk_ast(parsed.root_node)
    """

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self._timeout = timeout_seconds
        self._parsers: Dict[Language, object] = {}

    def _get_parser(self, language: Language) -> Optional[object]:
        """Return a cached Parser for the given language."""
        if not _TREE_SITTER_AVAILABLE:
            return None
        if language not in _LANG_MAP:
            return None
        if language not in self._parsers:
            p = TSParser(_LANG_MAP[language])  # type: ignore[call-arg]
            self._parsers[language] = p
        return self._parsers[language]

    def parse_source(
        self, source: str, language: Language, file_path: str = "<unknown>"
    ) -> ParsedFile:
        """Parse a source string and return a ParsedFile."""
        parser = self._get_parser(language)

        if parser is None:
            return ParsedFile(
                file_path=file_path,
                language=language,
                source=source,
                tree=None,
                root_node=None,
                parse_status=ParseStatus.UNSUPPORTED
                if not _TREE_SITTER_AVAILABLE
                else ParseStatus.UNSUPPORTED,
                error="No parser available for this language.",
            )

        start = time.perf_counter()
        try:
            encoded = source.encode("utf-8", errors="replace")
            tree = parser.parse(encoded)  # type: ignore[union-attr]
            elapsed_ms = (time.perf_counter() - start) * 1000

            error_count = self._count_errors(tree.root_node)
            return ParsedFile(
                file_path=file_path,
                language=language,
                source=source,
                tree=tree,
                root_node=tree.root_node,
                parse_status=ParseStatus.PARSED,
                parse_time_ms=elapsed_ms,
                error_count=error_count,
            )
        except Exception as e:
            logger.warning("Parse error in %s: %s", file_path, e)
            return ParsedFile(
                file_path=file_path,
                language=language,
                source=source,
                tree=None,
                root_node=None,
                parse_status=ParseStatus.FAILED,
                error=str(e),
            )

    def parse_file(
        self,
        file_path: str | Path,
        language: Language,
        source: Optional[str] = None,
    ) -> ParsedFile:
        """Read and parse a file. Optionally accepts pre-read source text."""
        path = Path(file_path)
        if source is None:
            try:
                source = path.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                return ParsedFile(
                    file_path=str(file_path),
                    language=language,
                    source="",
                    tree=None,
                    root_node=None,
                    parse_status=ParseStatus.FAILED,
                    error=str(e),
                )
        return self.parse_source(source, language, str(file_path))

    def is_available(self) -> bool:
        return _TREE_SITTER_AVAILABLE

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _count_errors(node: object) -> int:
        """Recursively count ERROR nodes in the AST."""
        if not _TREE_SITTER_AVAILABLE:
            return 0
        count = 0
        stack = [node]
        while stack:
            n = stack.pop()
            if n.type == "ERROR":  # type: ignore[union-attr]
                count += 1
            stack.extend(n.children)  # type: ignore[union-attr]
        return count
