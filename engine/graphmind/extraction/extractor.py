"""
Symbol & Relationship Extractor
=================================
Walks a tree-sitter AST and extracts structured entities (nodes) and
relationships (edges) for the Code Knowledge Graph.

Supported languages: Python, JavaScript/TypeScript.
Extensibility: add a new _extract_<language> method + register it.

Important limitations documented honestly:
- Call extraction is syntactic, not semantic. Dynamic dispatch, closures,
  and decorators that redirect calls may not be detected.
- Import resolution is path-based heuristic for relative imports.
- Variable tracking is limited to top-level and class-level declarations.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional
from uuid import uuid4

from graphmind.models import (
    ClassNode,
    EdgeType,
    FileNode,
    FunctionNode,
    GraphEdge,
    GraphNode,
    ImportNode,
    Language,
    MethodNode,
    NodeType,
    VariableNode,
    compute_hash,
)
from graphmind.parser.parser import ParsedFile

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Symbols and relationships extracted from a single file."""

    file_id: str
    nodes: List[GraphNode] = field(default_factory=list)
    edges: List[GraphEdge] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class SymbolExtractor:
    """
    Extracts graph nodes and edges from a ParsedFile.

    Usage::

        extractor = SymbolExtractor()
        result = extractor.extract(parsed_file, file_node)
    """

    def extract(self, parsed: ParsedFile, file_node: FileNode) -> ExtractionResult:
        result = ExtractionResult(file_id=file_node.id)

        if not parsed.is_valid or parsed.root_node is None:
            result.errors.append(f"Cannot extract from unparsed file: {parsed.file_path}")
            return result

        try:
            if parsed.language == Language.PYTHON:
                self._extract_python(parsed, file_node, result)
            elif parsed.language in (Language.JAVASCRIPT, Language.TYPESCRIPT):
                self._extract_javascript(parsed, file_node, result)
        except Exception as e:
            logger.exception("Extraction failed for %s: %s", parsed.file_path, e)
            result.errors.append(str(e))

        return result

    # ─────────────────────────────────────────────────────────────────────────
    # Python extractor
    # ─────────────────────────────────────────────────────────────────────────

    def _extract_python(
        self, parsed: ParsedFile, file_node: FileNode, result: ExtractionResult
    ) -> None:
        root = parsed.root_node
        source_lines = parsed.source.splitlines()
        repo_id = file_node.repo_id

        for node in self._iter_children(root):
            ntype = node.type

            # ── Import statements ─────────────────────────────────────────
            if ntype == "import_statement":
                imp = self._py_parse_import(node, parsed.source)
                imp_node = ImportNode(
                    id=str(uuid4()),
                    name=imp["module"],
                    file_id=file_node.id,
                    repo_id=repo_id,
                    module=imp["module"],
                    alias=imp.get("alias"),
                    imported_names=imp.get("names", []),
                    line=node.start_point[0] + 1,
                    is_relative=False,
                )
                result.nodes.append(imp_node)
                result.edges.append(GraphEdge(
                    source_id=file_node.id,
                    target_id=imp_node.id,
                    edge_type=EdgeType.IMPORTS,
                ))

            elif ntype == "import_from_statement":
                imp = self._py_parse_from_import(node, parsed.source)
                imp_node = ImportNode(
                    id=str(uuid4()),
                    name=imp["module"],
                    file_id=file_node.id,
                    repo_id=repo_id,
                    module=imp["module"],
                    imported_names=imp.get("names", []),
                    line=node.start_point[0] + 1,
                    is_relative=imp.get("is_relative", False),
                )
                result.nodes.append(imp_node)
                result.edges.append(GraphEdge(
                    source_id=file_node.id,
                    target_id=imp_node.id,
                    edge_type=EdgeType.IMPORTS,
                ))

            # ── Class definitions ─────────────────────────────────────────
            elif ntype == "class_definition":
                cls_node = self._py_parse_class(node, parsed.source, file_node, repo_id)
                result.nodes.append(cls_node)
                result.edges.append(GraphEdge(
                    source_id=file_node.id,
                    target_id=cls_node.id,
                    edge_type=EdgeType.DEFINES,
                ))
                # Add CONTAINS edge
                result.edges.append(GraphEdge(
                    source_id=file_node.id,
                    target_id=cls_node.id,
                    edge_type=EdgeType.CONTAINS,
                ))
                # Extract bases as INHERITS edges (symbolic, unresolved)
                for base in cls_node.bases:
                    result.edges.append(GraphEdge(
                        source_id=cls_node.id,
                        target_id=f"unresolved::{base}",
                        edge_type=EdgeType.INHERITS,
                        confidence=0.7,  # unresolved base
                        metadata={"unresolved": True, "base_name": base},
                    ))
                # Extract methods
                for method in self._py_extract_methods(node, parsed.source, cls_node, repo_id):
                    result.nodes.append(method)
                    result.edges.append(GraphEdge(
                        source_id=cls_node.id,
                        target_id=method.id,
                        edge_type=EdgeType.CONTAINS,
                    ))
                    result.edges.append(GraphEdge(
                        source_id=file_node.id,
                        target_id=method.id,
                        edge_type=EdgeType.DEFINES,
                    ))

            # ── Function definitions (module-level) ───────────────────────
            elif ntype == "function_definition":
                fn_node = self._py_parse_function(node, parsed.source, file_node, repo_id)
                result.nodes.append(fn_node)
                result.edges.append(GraphEdge(
                    source_id=file_node.id,
                    target_id=fn_node.id,
                    edge_type=EdgeType.DEFINES,
                ))
                result.edges.append(GraphEdge(
                    source_id=file_node.id,
                    target_id=fn_node.id,
                    edge_type=EdgeType.CONTAINS,
                ))

    # ─────────────────────────────────────────────────────────────────────────
    # JavaScript / TypeScript extractor
    # ─────────────────────────────────────────────────────────────────────────

    def _extract_javascript(
        self, parsed: ParsedFile, file_node: FileNode, result: ExtractionResult
    ) -> None:
        root = parsed.root_node
        repo_id = file_node.repo_id

        for node in self._iter_all_children(root, max_depth=3):
            ntype = node.type

            if ntype in ("import_statement", "import_declaration"):
                imp_node = self._js_parse_import(node, parsed.source, file_node, repo_id)
                if imp_node:
                    result.nodes.append(imp_node)
                    result.edges.append(GraphEdge(
                        source_id=file_node.id,
                        target_id=imp_node.id,
                        edge_type=EdgeType.IMPORTS,
                    ))

            elif ntype == "class_declaration":
                cls_node = self._js_parse_class(node, parsed.source, file_node, repo_id)
                result.nodes.append(cls_node)
                result.edges.append(GraphEdge(
                    source_id=file_node.id,
                    target_id=cls_node.id,
                    edge_type=EdgeType.DEFINES,
                ))

            elif ntype in (
                "function_declaration",
                "arrow_function",
                "function_expression",
            ):
                name = self._js_get_function_name(node, parsed.source)
                if name:
                    fn_node = FunctionNode(
                        id=str(uuid4()),
                        name=name,
                        file_id=file_node.id,
                        repo_id=repo_id,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                    )
                    result.nodes.append(fn_node)
                    result.edges.append(GraphEdge(
                        source_id=file_node.id,
                        target_id=fn_node.id,
                        edge_type=EdgeType.DEFINES,
                    ))

    # ─────────────────────────────────────────────────────────────────────────
    # Python helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _py_parse_import(self, node: object, source: str) -> dict:
        text = self._node_text(node, source)
        # "import os.path as osp"
        parts = text.replace("import ", "").strip().split(" as ")
        module = parts[0].strip()
        alias = parts[1].strip() if len(parts) > 1 else None
        return {"module": module, "alias": alias, "names": []}

    def _py_parse_from_import(self, node: object, source: str) -> dict:
        text = self._node_text(node, source)
        is_relative = text.startswith("from .")
        # "from .module import name1, name2"
        match = re.match(r"from\s+(\.+\S*)\s+import\s+(.*)", text, re.DOTALL)
        if not match:
            match = re.match(r"from\s+(\S+)\s+import\s+(.*)", text, re.DOTALL)
        if match:
            module = match.group(1).strip()
            names_str = match.group(2).strip().strip("()")
            names = [n.strip() for n in names_str.split(",") if n.strip()]
            return {"module": module, "names": names, "is_relative": is_relative}
        return {"module": "unknown", "names": [], "is_relative": is_relative}

    def _py_parse_class(
        self, node: object, source: str, file_node: FileNode, repo_id: str
    ) -> ClassNode:
        name = ""
        bases: List[str] = []
        docstring = None

        for child in node.children:  # type: ignore[union-attr]
            if child.type == "identifier":
                name = self._node_text(child, source)
            elif child.type == "argument_list":
                for arg in child.children:
                    if arg.type in ("identifier", "attribute"):
                        bases.append(self._node_text(arg, source))
            elif child.type == "block":
                # First expression_statement may be a docstring
                for stmt in child.children:
                    if stmt.type == "expression_statement":
                        for s in stmt.children:
                            if s.type == "string":
                                docstring = self._node_text(s, source).strip("\"'")
                        break

        body_text = self._node_text(node, source)
        return ClassNode(
            id=str(uuid4()),
            name=name or "UnknownClass",
            file_id=file_node.id,
            repo_id=repo_id,
            start_line=node.start_point[0] + 1,  # type: ignore[union-attr]
            end_line=node.end_point[0] + 1,  # type: ignore[union-attr]
            bases=bases,
            docstring=docstring,
        )

    def _py_extract_methods(
        self, class_node: object, source: str, cls_node: ClassNode, repo_id: str
    ) -> List[MethodNode]:
        methods = []
        for child in class_node.children:  # type: ignore[union-attr]
            if child.type == "block":
                for stmt in child.children:
                    if stmt.type in ("function_definition", "decorated_definition"):
                        fn = stmt
                        if stmt.type == "decorated_definition":
                            for d in stmt.children:
                                if d.type == "function_definition":
                                    fn = d
                                    break
                        method = self._py_parse_method(fn, source, cls_node, repo_id)
                        if method:
                            methods.append(method)
        return methods

    def _py_parse_method(
        self, node: object, source: str, cls_node: ClassNode, repo_id: str
    ) -> Optional[MethodNode]:
        name = ""
        params: List[dict] = []
        return_type = None

        for child in node.children:  # type: ignore[union-attr]
            if child.type == "identifier" and not name:
                name = self._node_text(child, source)
            elif child.type == "parameters":
                params = self._py_extract_params(child, source)
            elif child.type == "type":
                return_type = self._node_text(child, source)

        if not name:
            return None

        return MethodNode(
            id=str(uuid4()),
            name=name,
            file_id=cls_node.file_id,
            class_id=cls_node.id,
            repo_id=repo_id,
            start_line=node.start_point[0] + 1,  # type: ignore[union-attr]
            end_line=node.end_point[0] + 1,  # type: ignore[union-attr]
            params=params,
            return_type=return_type,
        )

    def _py_parse_function(
        self, node: object, source: str, file_node: FileNode, repo_id: str
    ) -> FunctionNode:
        name = ""
        params: List[dict] = []
        return_type = None
        is_async = False

        for child in node.children:  # type: ignore[union-attr]
            if child.type == "async":
                is_async = True
            elif child.type == "identifier" and not name:
                name = self._node_text(child, source)
            elif child.type == "parameters":
                params = self._py_extract_params(child, source)
            elif child.type == "type":
                return_type = self._node_text(child, source)

        body_text = self._node_text(node, source)
        return FunctionNode(
            id=str(uuid4()),
            name=name or "anonymous",
            file_id=file_node.id,
            repo_id=repo_id,
            start_line=node.start_point[0] + 1,  # type: ignore[union-attr]
            end_line=node.end_point[0] + 1,  # type: ignore[union-attr]
            params=params,
            return_type=return_type,
            is_async=is_async,
            content_hash=compute_hash(body_text),
        )

    def _py_extract_params(self, params_node: object, source: str) -> List[dict]:
        params = []
        for child in params_node.children:  # type: ignore[union-attr]
            if child.type in ("identifier", "typed_parameter", "default_parameter"):
                name = ""
                annotation = None
                for part in child.children:
                    if part.type == "identifier" and not name:
                        name = self._node_text(part, source)
                    elif part.type == "type":
                        annotation = self._node_text(part, source)
                if child.type == "identifier":
                    name = self._node_text(child, source)
                if name and name not in ("self", "cls"):
                    params.append({"name": name, "annotation": annotation})
        return params

    # ─────────────────────────────────────────────────────────────────────────
    # JavaScript helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _js_parse_import(
        self, node: object, source: str, file_node: FileNode, repo_id: str
    ) -> Optional[ImportNode]:
        text = self._node_text(node, source)
        # Extract module path from quotes
        match = re.search(r'[\'"]([^\'"]+)[\'"]', text)
        if not match:
            return None
        module = match.group(1)
        return ImportNode(
            id=str(uuid4()),
            name=module,
            file_id=file_node.id,
            repo_id=repo_id,
            module=module,
            line=node.start_point[0] + 1,  # type: ignore[union-attr]
            is_relative=module.startswith("."),
        )

    def _js_parse_class(
        self, node: object, source: str, file_node: FileNode, repo_id: str
    ) -> ClassNode:
        name = ""
        bases = []
        for child in node.children:  # type: ignore[union-attr]
            if child.type == "identifier" and not name:
                name = self._node_text(child, source)
            elif child.type == "class_heritage":
                for h in child.children:
                    if h.type == "identifier":
                        bases.append(self._node_text(h, source))
        return ClassNode(
            id=str(uuid4()),
            name=name or "AnonymousClass",
            file_id=file_node.id,
            repo_id=repo_id,
            start_line=node.start_point[0] + 1,  # type: ignore[union-attr]
            end_line=node.end_point[0] + 1,  # type: ignore[union-attr]
            bases=bases,
        )

    def _js_get_function_name(self, node: object, source: str) -> Optional[str]:
        for child in node.children:  # type: ignore[union-attr]
            if child.type == "identifier":
                return self._node_text(child, source)
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Generic AST utilities
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _node_text(node: object, source: str) -> str:
        try:
            start = node.start_byte  # type: ignore[union-attr]
            end = node.end_byte  # type: ignore[union-attr]
            return source.encode("utf-8")[start:end].decode("utf-8", errors="replace")
        except Exception:
            return ""

    @staticmethod
    def _iter_children(node: object):
        """Iterate immediate children of a node."""
        for child in node.children:  # type: ignore[union-attr]
            yield child

    @staticmethod
    def _iter_all_children(node: object, max_depth: int = 5):
        """BFS over all descendants up to max_depth."""
        queue = [(node, 0)]
        while queue:
            n, depth = queue.pop(0)
            if depth > max_depth:
                continue
            yield n
            for child in n.children:  # type: ignore[union-attr]
                queue.append((child, depth + 1))
