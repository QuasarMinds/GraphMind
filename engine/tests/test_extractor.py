"""
Tests: Symbol & Relationship Extractor  (Phase 2)
==================================================
Verifies that the SymbolExtractor correctly extracts classes, functions,
methods, imports, edges, and decorators from Python and JavaScript source.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from graphmind.extraction.extractor import SymbolExtractor
from graphmind.models import (
    EdgeType,
    FileNode,
    Language,
    NodeType,
    ParseStatus,
)
from graphmind.parser.parser import ParsedFile, SourceParser

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures & helpers
# ─────────────────────────────────────────────────────────────────────────────


def _file_node(lang: Language = Language.PYTHON, name: str = "test.py") -> FileNode:
    return FileNode(
        id=str(uuid4()),
        name=name,
        path=f"src/{name}",
        repo_id="repo-test",
        language=lang,
        parse_status=ParseStatus.PARSED,
    )


@pytest.fixture
def parser() -> SourceParser:
    return SourceParser()


@pytest.fixture
def extractor() -> SymbolExtractor:
    return SymbolExtractor()


# ─────────────────────────────────────────────────────────────────────────────
# Python source fixtures
# ─────────────────────────────────────────────────────────────────────────────

PYTHON_SRC = '''\
import os
from pathlib import Path

class MyClass(BaseClass):
    """A sample class."""

    def __init__(self, name: str) -> None:
        self.name = name

    def greet(self) -> str:
        return f"Hello {self.name}"

    @staticmethod
    def helper() -> None:
        pass

    @classmethod
    def create(cls) -> "MyClass":
        return cls("default")

def standalone_fn(x: int, y: int) -> int:
    return x + y

async def async_fn() -> None:
    pass

def caller():
    standalone_fn(1, 2)

MAX_SIZE = 100
DEBUG_MODE = True
'''

JS_SRC = """\
import { useState, useEffect } from 'react';
import MyLib from './mylib';

class Counter {
    constructor(start) {
        this.count = start;
    }
    increment() {
        this.count += 1;
    }
    reset() {
        this.count = 0;
    }
}

function add(a, b) {
    return a + b;
}

const multiply = (a, b) => a * b;
const divide = function(a, b) { return a / b; };
"""


# ─────────────────────────────────────────────────────────────────────────────
# Python extraction tests
# ─────────────────────────────────────────────────────────────────────────────


def test_py_extract_imports(parser: SourceParser, extractor: SymbolExtractor):
    fn = _file_node()
    parsed = parser.parse_source(PYTHON_SRC, Language.PYTHON, "test.py")
    assert parsed.is_valid, "Tree-sitter must be available for extraction tests"
    result = extractor.extract(parsed, fn)
    names = {n.name for n in result.nodes if n.node_type == NodeType.IMPORT}
    assert "os" in names
    assert "pathlib" in names


def test_py_extract_class(parser: SourceParser, extractor: SymbolExtractor):
    fn = _file_node()
    parsed = parser.parse_source(PYTHON_SRC, Language.PYTHON, "test.py")
    result = extractor.extract(parsed, fn)
    classes = [n for n in result.nodes if n.node_type == NodeType.CLASS]
    assert len(classes) == 1
    assert classes[0].name == "MyClass"
    assert "BaseClass" in classes[0].bases  # type: ignore[attr-defined]


def test_py_extract_methods(parser: SourceParser, extractor: SymbolExtractor):
    fn = _file_node()
    parsed = parser.parse_source(PYTHON_SRC, Language.PYTHON, "test.py")
    result = extractor.extract(parsed, fn)
    method_names = {n.name for n in result.nodes if n.node_type == NodeType.METHOD}
    assert "__init__" in method_names
    assert "greet" in method_names
    assert "helper" in method_names
    assert "create" in method_names


def test_py_extract_functions(parser: SourceParser, extractor: SymbolExtractor):
    fn = _file_node()
    parsed = parser.parse_source(PYTHON_SRC, Language.PYTHON, "test.py")
    result = extractor.extract(parsed, fn)
    fn_names = {n.name for n in result.nodes if n.node_type == NodeType.FUNCTION}
    assert "standalone_fn" in fn_names
    assert "async_fn" in fn_names
    assert "caller" in fn_names


def test_py_async_function_flag(parser: SourceParser, extractor: SymbolExtractor):
    fn = _file_node()
    parsed = parser.parse_source(PYTHON_SRC, Language.PYTHON, "test.py")
    result = extractor.extract(parsed, fn)
    async_fns = [
        n for n in result.nodes
        if n.node_type == NodeType.FUNCTION and getattr(n, "is_async", False)
    ]
    assert any(n.name == "async_fn" for n in async_fns)


def test_py_static_method_flag(parser: SourceParser, extractor: SymbolExtractor):
    fn = _file_node()
    parsed = parser.parse_source(PYTHON_SRC, Language.PYTHON, "test.py")
    result = extractor.extract(parsed, fn)
    methods = [n for n in result.nodes if n.node_type == NodeType.METHOD]
    helper = next((m for m in methods if m.name == "helper"), None)
    assert helper is not None
    assert helper.is_static is True  # type: ignore[attr-defined]


def test_py_classmethod_flag(parser: SourceParser, extractor: SymbolExtractor):
    fn = _file_node()
    parsed = parser.parse_source(PYTHON_SRC, Language.PYTHON, "test.py")
    result = extractor.extract(parsed, fn)
    methods = [n for n in result.nodes if n.node_type == NodeType.METHOD]
    create = next((m for m in methods if m.name == "create"), None)
    assert create is not None
    assert create.is_class_method is True  # type: ignore[attr-defined]


def test_py_defines_edges(parser: SourceParser, extractor: SymbolExtractor):
    fn = _file_node()
    parsed = parser.parse_source(PYTHON_SRC, Language.PYTHON, "test.py")
    result = extractor.extract(parsed, fn)
    defines = [e for e in result.edges if e.edge_type == EdgeType.DEFINES]
    assert len(defines) >= 3  # class + 2 functions minimum


def test_py_contains_edges(parser: SourceParser, extractor: SymbolExtractor):
    fn = _file_node()
    parsed = parser.parse_source(PYTHON_SRC, Language.PYTHON, "test.py")
    result = extractor.extract(parsed, fn)
    contains = [e for e in result.edges if e.edge_type == EdgeType.CONTAINS]
    # file→class + class→methods
    assert len(contains) >= 3


def test_py_inherits_edge(parser: SourceParser, extractor: SymbolExtractor):
    fn = _file_node()
    parsed = parser.parse_source(PYTHON_SRC, Language.PYTHON, "test.py")
    result = extractor.extract(parsed, fn)
    inherits = [e for e in result.edges if e.edge_type == EdgeType.INHERITS]
    assert len(inherits) == 1
    assert inherits[0].metadata.get("base_name") == "BaseClass"
    assert inherits[0].confidence < 1.0  # unresolved → confidence < 1


def test_py_calls_edges(parser: SourceParser, extractor: SymbolExtractor):
    fn = _file_node()
    parsed = parser.parse_source(PYTHON_SRC, Language.PYTHON, "test.py")
    result = extractor.extract(parsed, fn)
    calls = [e for e in result.edges if e.edge_type == EdgeType.CALLS]
    # caller() calls standalone_fn()
    assert len(calls) >= 1


def test_py_imports_edges(parser: SourceParser, extractor: SymbolExtractor):
    fn = _file_node()
    parsed = parser.parse_source(PYTHON_SRC, Language.PYTHON, "test.py")
    result = extractor.extract(parsed, fn)
    imports = [e for e in result.edges if e.edge_type == EdgeType.IMPORTS]
    assert len(imports) >= 2


def test_py_no_extraction_errors(parser: SourceParser, extractor: SymbolExtractor):
    fn = _file_node()
    parsed = parser.parse_source(PYTHON_SRC, Language.PYTHON, "test.py")
    result = extractor.extract(parsed, fn)
    assert result.errors == []


def test_py_extraction_on_failed_parse(extractor: SymbolExtractor):
    """Extractor must return empty + error message for an unparsed file."""
    parsed = ParsedFile(
        file_path="bad.py",
        language=Language.PYTHON,
        source="",
        tree=None,
        root_node=None,
        parse_status=ParseStatus.FAILED,
    )
    fn = _file_node()
    result = extractor.extract(parsed, fn)
    assert len(result.nodes) == 0
    assert len(result.errors) > 0


# ─────────────────────────────────────────────────────────────────────────────
# JavaScript extraction tests
# ─────────────────────────────────────────────────────────────────────────────


def test_js_extract_imports(parser: SourceParser, extractor: SymbolExtractor):
    fn = _file_node(Language.JAVASCRIPT, "test.js")
    parsed = parser.parse_source(JS_SRC, Language.JAVASCRIPT, "test.js")
    assert parsed.is_valid
    result = extractor.extract(parsed, fn)
    modules = {n.name for n in result.nodes if n.node_type == NodeType.IMPORT}
    assert "react" in modules
    assert "./mylib" in modules


def test_js_extract_class(parser: SourceParser, extractor: SymbolExtractor):
    fn = _file_node(Language.JAVASCRIPT, "test.js")
    parsed = parser.parse_source(JS_SRC, Language.JAVASCRIPT, "test.js")
    result = extractor.extract(parsed, fn)
    classes = [n for n in result.nodes if n.node_type == NodeType.CLASS]
    assert len(classes) == 1
    assert classes[0].name == "Counter"


def test_js_extract_class_methods(parser: SourceParser, extractor: SymbolExtractor):
    fn = _file_node(Language.JAVASCRIPT, "test.js")
    parsed = parser.parse_source(JS_SRC, Language.JAVASCRIPT, "test.js")
    result = extractor.extract(parsed, fn)
    method_names = {n.name for n in result.nodes if n.node_type == NodeType.METHOD}
    assert "constructor" in method_names
    assert "increment" in method_names
    assert "reset" in method_names


def test_js_extract_function(parser: SourceParser, extractor: SymbolExtractor):
    fn = _file_node(Language.JAVASCRIPT, "test.js")
    parsed = parser.parse_source(JS_SRC, Language.JAVASCRIPT, "test.js")
    result = extractor.extract(parsed, fn)
    fn_names = {n.name for n in result.nodes if n.node_type == NodeType.FUNCTION}
    assert "add" in fn_names


def test_js_extract_arrow_functions(parser: SourceParser, extractor: SymbolExtractor):
    fn = _file_node(Language.JAVASCRIPT, "test.js")
    parsed = parser.parse_source(JS_SRC, Language.JAVASCRIPT, "test.js")
    result = extractor.extract(parsed, fn)
    fn_names = {n.name for n in result.nodes if n.node_type == NodeType.FUNCTION}
    assert "multiply" in fn_names


def test_js_no_extraction_errors(parser: SourceParser, extractor: SymbolExtractor):
    fn = _file_node(Language.JAVASCRIPT, "test.js")
    parsed = parser.parse_source(JS_SRC, Language.JAVASCRIPT, "test.js")
    result = extractor.extract(parsed, fn)
    assert result.errors == []

