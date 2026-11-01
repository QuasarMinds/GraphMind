"""
AST Visitor Utilities
======================
Generic tree-sitter AST visitor patterns used by the extractor layer.
Provides node iteration, depth-limited BFS traversal, node text extraction,
and search helpers — without coupling to any specific language.

All functions accept plain `object` types so they work regardless of whether
tree-sitter is available (callers are expected to guard on availability).
"""

from __future__ import annotations

from typing import Generator, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Text extraction
# ─────────────────────────────────────────────────────────────────────────────


def node_text(node: object, source: str) -> str:
    """Return the source substring covered by *node*."""
    try:
        start: int = node.start_byte  # type: ignore[union-attr]
        end: int = node.end_byte      # type: ignore[union-attr]
        return source.encode("utf-8")[start:end].decode("utf-8", errors="replace")
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# Child iteration
# ─────────────────────────────────────────────────────────────────────────────


def iter_children(node: object) -> Generator[object, None, None]:
    """Yield immediate children of *node*."""
    try:
        for child in node.children:  # type: ignore[union-attr]
            yield child
    except (AttributeError, TypeError):
        return


def iter_descendants(
    node: object, max_depth: int = 10
) -> Generator[Tuple[object, int], None, None]:
    """
    BFS over all descendant nodes up to *max_depth*.
    Yields ``(node, depth)`` tuples.  Root node is yielded at depth 0.
    """
    queue: list = [(node, 0)]
    while queue:
        n, depth = queue.pop(0)
        yield n, depth
        if depth < max_depth:
            try:
                for child in n.children:  # type: ignore[union-attr]
                    queue.append((child, depth + 1))
            except (AttributeError, TypeError):
                pass


# ─────────────────────────────────────────────────────────────────────────────
# Search helpers
# ─────────────────────────────────────────────────────────────────────────────


def find_child_by_type(node: object, *types: str) -> Optional[object]:
    """Return the first immediate child whose ``type`` is in *types*."""
    for child in iter_children(node):
        try:
            if child.type in types:  # type: ignore[union-attr]
                return child
        except AttributeError:
            pass
    return None


def find_all_descendants_by_type(
    node: object, *types: str, max_depth: int = 10
) -> List[object]:
    """Return all descendant nodes (including self) matching any of *types*."""
    results: List[object] = []
    for n, _ in iter_descendants(node, max_depth=max_depth):
        try:
            if n.type in types:  # type: ignore[union-attr]
                results.append(n)
        except AttributeError:
            pass
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Error counting
# ─────────────────────────────────────────────────────────────────────────────


def count_error_nodes(node: object) -> int:
    """Recursively count ERROR nodes in the subtree rooted at *node*."""
    count = 0
    stack = [node]
    while stack:
        n = stack.pop()
        try:
            if n.type == "ERROR":  # type: ignore[union-attr]
                count += 1
            stack.extend(n.children)  # type: ignore[union-attr]
        except (AttributeError, TypeError):
            pass
    return count
