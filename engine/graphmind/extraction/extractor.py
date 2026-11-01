"""
Symbol & Relationship Extractor
=================================
Walks a tree-sitter AST and extracts structured entities (nodes) and
relationships (edges) for the Code Knowledge Graph.

Supported languages  : Python, JavaScript, TypeScript.
Extensibility        : add a new _extract_<language> method + register it
                       in ``extract()``.

Documented limitations
----------------------
- Call extraction is *syntactic*, not semantic.  Dynamic dispatch, closures,
  higher-order functions and decorator-redirected calls may not be detected.
- Import resolution is path-based heuristic for relative imports only.
- Variable tracking is limited to module-level ALL_CAPS constants.
- Cross-file symbol resolution (CALLS to external functions) is deferred to
  Phase 4 (hybrid retrieval pass).
- TypeScript type information is extracted as raw strings, not resolved.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from uuid import uuid4

from graphmind.ast.visitor import (
    find_all_descendants_by_type,
    find_child_by_type,
    iter_children,
    iter_descendants,
    node_text,
)
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
            result.errors.append(
                f"Cannot extract from unparsed file: {parsed.file_path}"
            )
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
        source = parsed.source
        repo_id = file_node.repo_id

        # symbol_map: local name → node_id  (used for intra-file CALLS)
        symbol_map: Dict[str, str] = {}

        for node in iter_children(root):
            ntype = node.type  # type: ignore[union-attr]

            # ── Imports ───────────────────────────────────────────────────
            if ntype == "import_statement":
                imp = self._py_parse_import(node, source)
                imp_node = ImportNode(
                    id=str(uuid4()),
                    name=imp["module"],
                    file_id=file_node.id,
                    repo_id=repo_id,
                    module=imp["module"],
                    alias=imp.get("alias"),
                    imported_names=imp.get("names", []),
                    line=node.start_point[0] + 1,  # type: ignore[union-attr]
                    is_relative=False,
                )
                result.nodes.append(imp_node)
                result.edges.append(
                    GraphEdge(
                        source_id=file_node.id,
                        target_id=imp_node.id,
                        edge_type=EdgeType.IMPORTS,
                    )
                )

            elif ntype == "import_from_statement":
                imp = self._py_parse_from_import(node, source)
                imp_node = ImportNode(
                    id=str(uuid4()),
                    name=imp["module"],
                    file_id=file_node.id,
                    repo_id=repo_id,
                    module=imp["module"],
                    imported_names=imp.get("names", []),
                    line=node.start_point[0] + 1,  # type: ignore[union-attr]
                    is_relative=imp.get("is_relative", False),
                )
                result.nodes.append(imp_node)
                result.edges.append(
                    GraphEdge(
                        source_id=file_node.id,
                        target_id=imp_node.id,
                        edge_type=EdgeType.IMPORTS,
                    )
                )

            # ── Class definitions ─────────────────────────────────────────
            elif ntype == "class_definition":
                cls_node = self._py_parse_class(node, source, file_node, repo_id)
                symbol_map[cls_node.name] = cls_node.id
                result.nodes.append(cls_node)
                result.edges.append(
                    GraphEdge(
                        source_id=file_node.id,
                        target_id=cls_node.id,
                        edge_type=EdgeType.DEFINES,
                    )
                )
                result.edges.append(
                    GraphEdge(
                        source_id=file_node.id,
                        target_id=cls_node.id,
                        edge_type=EdgeType.CONTAINS,
                    )
                )
                # Unresolved INHERITS edges (marked with confidence < 1.0)
                for base in cls_node.bases:
                    result.edges.append(
                        GraphEdge(
                            source_id=cls_node.id,
                            target_id=f"unresolved::{base}",
                            edge_type=EdgeType.INHERITS,
                            confidence=0.7,
                            metadata={"unresolved": True, "base_name": base},
                        )
                    )
                # Extract methods
                for method in self._py_extract_methods(
                    node, source, cls_node, repo_id
                ):
                    symbol_map[f"{cls_node.name}.{method.name}"] = method.id
                    result.nodes.append(method)
                    result.edges.append(
                        GraphEdge(
                            source_id=cls_node.id,
                            target_id=method.id,
                            edge_type=EdgeType.CONTAINS,
                        )
                    )
                    result.edges.append(
                        GraphEdge(
                            source_id=file_node.id,
                            target_id=method.id,
                            edge_type=EdgeType.DEFINES,
                        )
                    )

            # ── Module-level functions (possibly decorated) ────────────────
            elif ntype in ("function_definition", "decorated_definition"):
                decorators: List[str] = []
                fn_ast = node
                if ntype == "decorated_definition":
                    for child in iter_children(node):
                        if child.type == "decorator":  # type: ignore[union-attr]
                            decorators.append(
                                node_text(child, source).lstrip("@").strip()
                            )
                        elif child.type == "function_definition":  # type: ignore[union-attr]
                            fn_ast = child
                fn_node = self._py_parse_function(fn_ast, source, file_node, repo_id)
                fn_node.decorators = decorators
                symbol_map[fn_node.name] = fn_node.id
                result.nodes.append(fn_node)
                result.edges.append(
                    GraphEdge(
                        source_id=file_node.id,
                        target_id=fn_node.id,
                        edge_type=EdgeType.DEFINES,
                    )
                )
                result.edges.append(
                    GraphEdge(
                        source_id=file_node.id,
                        target_id=fn_node.id,
                        edge_type=EdgeType.CONTAINS,
                    )
                )

            # ── Module-level ALL_CAPS constants ───────────────────────────
            elif ntype == "expression_statement":
                var = self._py_parse_toplevel_var(node, source, file_node, repo_id)
                if var:
                    result.nodes.append(var)
                    result.edges.append(
                        GraphEdge(
                            source_id=file_node.id,
                            target_id=var.id,
                            edge_type=EdgeType.DEFINES,
                        )
                    )

        # Second pass: intra-file CALLS edges
        self._py_extract_calls(root, source, file_node, result, symbol_map)

    def _py_extract_calls(
        self,
        root: object,
        source: str,
        file_node: FileNode,
        result: ExtractionResult,
        symbol_map: Dict[str, str],
    ) -> None:
        """
        Detect call nodes inside the AST and emit CALLS edges for known symbols.

        Limitation: only intra-file calls to symbols we extracted are connected.
        Cross-file calls are not resolved here (Phase 4).
        """
        if not symbol_map:
            return

        for n, _ in iter_descendants(root, max_depth=20):
            if n.type != "call":  # type: ignore[union-attr]
                continue
            fn_child = find_child_by_type(n, "identifier", "attribute")
            if not fn_child:
                continue
            raw = node_text(fn_child, source)
            called = raw.split(".")[-1]
            if called not in symbol_map:
                continue
            enclosing = self._find_enclosing_symbol(n, result)
            src_id = enclosing if enclosing else file_node.id
            # Avoid self-loops
            if src_id == symbol_map[called]:
                continue
            result.edges.append(
                GraphEdge(
                    source_id=src_id,
                    target_id=symbol_map[called],
                    edge_type=EdgeType.CALLS,
                    confidence=0.8,
                    metadata={"intra_file": True},
                )
            )

    def _find_enclosing_symbol(
        self, call_node: object, result: ExtractionResult
    ) -> Optional[str]:
        """
        Return the ID of the tightest function/method that contains *call_node*
        (by line number comparison).
        """
        call_line: int = call_node.start_point[0] + 1  # type: ignore[union-attr]
        best_id: Optional[str] = None
        best_span: int = 10_000_000

        for n in result.nodes:
            if n.node_type not in (NodeType.FUNCTION, NodeType.METHOD):
                continue
            start = getattr(n, "start_line", 0)
            end = getattr(n, "end_line", 0)
            if start <= call_line <= end:
                span = end - start
                if span < best_span:
                    best_span = span
                    best_id = n.id
        return best_id

    # ─────────────────────────────────────────────────────────────────────────
    # JavaScript / TypeScript extractor
    # ─────────────────────────────────────────────────────────────────────────

    def _extract_javascript(
        self, parsed: ParsedFile, file_node: FileNode, result: ExtractionResult
    ) -> None:
        root = parsed.root_node
        source = parsed.source
        repo_id = file_node.repo_id
        symbol_map: Dict[str, str] = {}

        for n, depth in iter_descendants(root, max_depth=4):
            ntype = n.type  # type: ignore[union-attr]

            if ntype in ("import_statement", "import_declaration"):
                imp = self._js_parse_import(n, source, file_node, repo_id)
                if imp:
                    result.nodes.append(imp)
                    result.edges.append(
                        GraphEdge(
                            source_id=file_node.id,
                            target_id=imp.id,
                            edge_type=EdgeType.IMPORTS,
                        )
                    )

            elif ntype == "class_declaration":
                cls = self._js_parse_class(n, source, file_node, repo_id)
                symbol_map[cls.name] = cls.id
                result.nodes.append(cls)
                result.edges.append(
                    GraphEdge(
                        source_id=file_node.id,
                        target_id=cls.id,
                        edge_type=EdgeType.DEFINES,
                    )
                )
                result.edges.append(
                    GraphEdge(
                        source_id=file_node.id,
                        target_id=cls.id,
                        edge_type=EdgeType.CONTAINS,
                    )
                )
                for method in self._js_extract_class_methods(
                    n, source, cls, repo_id
                ):
                    symbol_map[f"{cls.name}.{method.name}"] = method.id
                    result.nodes.append(method)
                    result.edges.append(
                        GraphEdge(
                            source_id=cls.id,
                            target_id=method.id,
                            edge_type=EdgeType.CONTAINS,
                        )
                    )

            elif ntype == "function_declaration":
                name = self._js_fn_name(n, source)
                if name:
                    fn = FunctionNode(
                        id=str(uuid4()),
                        name=name,
                        file_id=file_node.id,
                        repo_id=repo_id,
                        start_line=n.start_point[0] + 1,  # type: ignore[union-attr]
                        end_line=n.end_point[0] + 1,  # type: ignore[union-attr]
                    )
                    symbol_map[name] = fn.id
                    result.nodes.append(fn)
                    result.edges.append(
                        GraphEdge(
                            source_id=file_node.id,
                            target_id=fn.id,
                            edge_type=EdgeType.DEFINES,
                        )
                    )

            elif ntype == "lexical_declaration" and depth <= 2:
                # const myFn = () => {} or const myFn = function() {}
                self._js_extract_arrow_fns(
                    n, source, file_node, repo_id, result, symbol_map
                )

        # CALLS pass
        self._js_extract_calls(root, source, file_node, result, symbol_map)

    def _js_extract_class_methods(
        self,
        class_node: object,
        source: str,
        cls_node: ClassNode,
        repo_id: str,
    ) -> List[MethodNode]:
        methods: List[MethodNode] = []
        for body, _ in iter_descendants(class_node, max_depth=2):
            if body.type != "class_body":  # type: ignore[union-attr]
                continue
            for member in iter_children(body):
                if member.type != "method_definition":  # type: ignore[union-attr]
                    continue
                name_node = find_child_by_type(
                    member, "property_identifier", "identifier"
                )
                if name_node:
                    m = MethodNode(
                        id=str(uuid4()),
                        name=node_text(name_node, source),
                        file_id=cls_node.file_id,
                        class_id=cls_node.id,
                        repo_id=repo_id,
                        start_line=member.start_point[0] + 1,  # type: ignore[union-attr]
                        end_line=member.end_point[0] + 1,  # type: ignore[union-attr]
                    )
                    methods.append(m)
        return methods

    def _js_extract_arrow_fns(
        self,
        lex_node: object,
        source: str,
        file_node: FileNode,
        repo_id: str,
        result: ExtractionResult,
        symbol_map: Dict[str, str],
    ) -> None:
        for child in iter_children(lex_node):
            if child.type != "variable_declarator":  # type: ignore[union-attr]
                continue
            name_node = find_child_by_type(child, "identifier")
            val_node: Optional[object] = None
            for vc in iter_children(child):
                if vc.type in ("arrow_function", "function_expression"):  # type: ignore[union-attr]
                    val_node = vc
            if name_node and val_node:
                name = node_text(name_node, source)
                fn = FunctionNode(
                    id=str(uuid4()),
                    name=name,
                    file_id=file_node.id,
                    repo_id=repo_id,
                    start_line=val_node.start_point[0] + 1,  # type: ignore[union-attr]
                    end_line=val_node.end_point[0] + 1,  # type: ignore[union-attr]
                )
                symbol_map[name] = fn.id
                result.nodes.append(fn)
                result.edges.append(
                    GraphEdge(
                        source_id=file_node.id,
                        target_id=fn.id,
                        edge_type=EdgeType.DEFINES,
                    )
                )

    def _js_extract_calls(
        self,
        root: object,
        source: str,
        file_node: FileNode,
        result: ExtractionResult,
        symbol_map: Dict[str, str],
    ) -> None:
        if not symbol_map:
            return
        for n, _ in iter_descendants(root, max_depth=20):
            if n.type != "call_expression":  # type: ignore[union-attr]
                continue
            fn_child = find_child_by_type(n, "identifier", "member_expression")
            if not fn_child:
                continue
            raw = node_text(fn_child, source)
            called = raw.split(".")[-1]
            if called not in symbol_map:
                continue
            enclosing = self._find_enclosing_symbol(n, result)
            src_id = enclosing if enclosing else file_node.id
            if src_id == symbol_map[called]:
                continue
            result.edges.append(
                GraphEdge(
                    source_id=src_id,
                    target_id=symbol_map[called],
                    edge_type=EdgeType.CALLS,
                    confidence=0.7,
                )
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Python parse helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _py_parse_import(self, node: object, source: str) -> dict:
        text = node_text(node, source)
        parts = text.replace("import ", "").strip().split(" as ")
        module = parts[0].strip()
        alias = parts[1].strip() if len(parts) > 1 else None
        return {"module": module, "alias": alias, "names": []}

    def _py_parse_from_import(self, node: object, source: str) -> dict:
        text = node_text(node, source)
        is_relative = text.startswith("from .")
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
        docstring: Optional[str] = None

        for child in iter_children(node):
            ctype = child.type  # type: ignore[union-attr]
            if ctype == "identifier":
                name = node_text(child, source)
            elif ctype == "argument_list":
                for arg in iter_children(child):
                    if arg.type in ("identifier", "attribute"):  # type: ignore[union-attr]
                        bases.append(node_text(arg, source))
            elif ctype == "block":
                for stmt in iter_children(child):
                    if stmt.type == "expression_statement":  # type: ignore[union-attr]
                        for s in iter_children(stmt):
                            if s.type in ("string", "concatenated_string"):  # type: ignore[union-attr]
                                docstring = node_text(s, source).strip("\"'")
                        break  # only check the first statement

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
        self,
        class_node: object,
        source: str,
        cls_node: ClassNode,
        repo_id: str,
    ) -> List[MethodNode]:
        methods: List[MethodNode] = []
        for child in iter_children(class_node):
            if child.type != "block":  # type: ignore[union-attr]
                continue
            for stmt in iter_children(child):
                decorators: List[str] = []
                fn = stmt
                if stmt.type == "decorated_definition":  # type: ignore[union-attr]
                    for d in iter_children(stmt):
                        if d.type == "decorator":  # type: ignore[union-attr]
                            decorators.append(
                                node_text(d, source).lstrip("@").strip()
                            )
                        elif d.type == "function_definition":  # type: ignore[union-attr]
                            fn = d
                if fn.type == "function_definition":  # type: ignore[union-attr]
                    m = self._py_parse_method(fn, source, cls_node, repo_id)
                    if m:
                        m.decorators = decorators
                        m.is_static = any("staticmethod" in d for d in decorators)
                        m.is_class_method = any(
                            "classmethod" in d for d in decorators
                        )
                        methods.append(m)
        return methods

    def _py_parse_method(
        self, node: object, source: str, cls_node: ClassNode, repo_id: str
    ) -> Optional[MethodNode]:
        name = ""
        params: List[dict] = []
        return_type: Optional[str] = None
        is_async = False

        for child in iter_children(node):
            ctype = child.type  # type: ignore[union-attr]
            if ctype == "async":
                is_async = True
            elif ctype == "identifier" and not name:
                name = node_text(child, source)
            elif ctype == "parameters":
                params = self._py_extract_params(child, source)
            elif ctype == "type":
                return_type = node_text(child, source)

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
            is_async=is_async,
        )

    def _py_parse_function(
        self, node: object, source: str, file_node: FileNode, repo_id: str
    ) -> FunctionNode:
        name = ""
        params: List[dict] = []
        return_type: Optional[str] = None
        is_async = False

        for child in iter_children(node):
            ctype = child.type  # type: ignore[union-attr]
            if ctype == "async":
                is_async = True
            elif ctype == "identifier" and not name:
                name = node_text(child, source)
            elif ctype == "parameters":
                params = self._py_extract_params(child, source)
            elif ctype == "type":
                return_type = node_text(child, source)

        body_text = node_text(node, source)
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
        params: List[dict] = []
        for child in iter_children(params_node):
            ctype = child.type  # type: ignore[union-attr]
            if ctype not in (
                "identifier",
                "typed_parameter",
                "default_parameter",
                "typed_default_parameter",
            ):
                continue
            name = ""
            annotation: Optional[str] = None
            if ctype == "identifier":
                name = node_text(child, source)
            else:
                for part in iter_children(child):
                    if part.type == "identifier" and not name:  # type: ignore[union-attr]
                        name = node_text(part, source)
                    elif part.type == "type":  # type: ignore[union-attr]
                        annotation = node_text(part, source)
            if name and name not in ("self", "cls"):
                params.append({"name": name, "annotation": annotation})
        return params

    def _py_parse_toplevel_var(
        self, node: object, source: str, file_node: FileNode, repo_id: str
    ) -> Optional[VariableNode]:
        """Detect module-level ALL_CAPS = … assignments as constant nodes."""
        text = node_text(node, source).strip()
        match = re.match(r"^([A-Z_][A-Z0-9_]{1,})\s*(?::\s*\S+)?\s*=", text)
        if match:
            var_name = match.group(1)
            return VariableNode(
                id=str(uuid4()),
                name=var_name,
                file_id=file_node.id,
                repo_id=repo_id,
                line=node.start_point[0] + 1,  # type: ignore[union-attr]
                is_constant=True,
            )
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # JavaScript parse helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _js_parse_import(
        self, node: object, source: str, file_node: FileNode, repo_id: str
    ) -> Optional[ImportNode]:
        text = node_text(node, source)
        match = re.search(r'[\'"]([^\'"]+)[\'"]', text)
        if not match:
            return None
        module = match.group(1)
        # Extract named imports from { a, b as c }
        names_match = re.search(r"\{([^}]+)\}", text)
        names: List[str] = []
        if names_match:
            names = [
                part.strip().split(" as ")[0].strip()
                for part in names_match.group(1).split(",")
                if part.strip()
            ]
        return ImportNode(
            id=str(uuid4()),
            name=module,
            file_id=file_node.id,
            repo_id=repo_id,
            module=module,
            imported_names=names,
            line=node.start_point[0] + 1,  # type: ignore[union-attr]
            is_relative=module.startswith("."),
        )

    def _js_parse_class(
        self, node: object, source: str, file_node: FileNode, repo_id: str
    ) -> ClassNode:
        name = ""
        bases: List[str] = []
        for child in iter_children(node):
            ctype = child.type  # type: ignore[union-attr]
            if ctype == "identifier" and not name:
                name = node_text(child, source)
            elif ctype == "class_heritage":
                for h in iter_children(child):
                    if h.type == "identifier":  # type: ignore[union-attr]
                        bases.append(node_text(h, source))
        return ClassNode(
            id=str(uuid4()),
            name=name or "AnonymousClass",
            file_id=file_node.id,
            repo_id=repo_id,
            start_line=node.start_point[0] + 1,  # type: ignore[union-attr]
            end_line=node.end_point[0] + 1,  # type: ignore[union-attr]
            bases=bases,
        )

    def _js_fn_name(self, node: object, source: str) -> Optional[str]:
        for child in iter_children(node):
            if child.type == "identifier":  # type: ignore[union-attr]
                return node_text(child, source)
        return None
