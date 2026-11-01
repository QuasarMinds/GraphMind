"""
Graph query and traversal routes.
Provides endpoints for browsing nodes, edges, traversal and search.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.main import get_engine
from graphmind.models import EdgeType, NodeType

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────────────────────────────────────


class TraversalRequest(BaseModel):
    start_node_id: str
    max_depth: int = 3
    edge_types: Optional[List[str]] = None
    max_nodes: int = 100


class TraversalStep(BaseModel):
    node: dict
    depth: int
    parent_id: Optional[str] = None
    via_edge_type: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Node endpoints
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/nodes")
def get_nodes(
    repo_id: Optional[str] = None,
    node_type: Optional[str] = None,
    limit: int = Query(default=500, le=2000),
    offset: int = 0,
):
    """List nodes with optional repo and type filtering."""
    engine = get_engine()
    nt = None
    if node_type:
        try:
            nt = NodeType(node_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown node_type: {node_type}")
    nodes = engine.graph.get_all_nodes(repo_id=repo_id, node_type=nt, limit=limit, offset=offset)
    return {"nodes": nodes, "count": len(nodes), "offset": offset}


@router.get("/nodes/{node_id}")
def get_node(node_id: str):
    """Return a single node and its immediate neighbors."""
    engine = get_engine()
    node = engine.graph.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found.")
    neighbors = engine.graph.get_neighbors(node_id)
    return {"node": {**node, "id": node_id}, "neighbors": neighbors}


@router.get("/nodes/{node_id}/neighbors")
def get_neighbors(
    node_id: str,
    direction: str = "both",
    edge_type: Optional[str] = None,
):
    """Return neighboring nodes of a given node."""
    engine = get_engine()
    if not engine.graph.has_node(node_id):
        raise HTTPException(status_code=404, detail="Node not found.")
    et = None
    if edge_type:
        try:
            et = [EdgeType(edge_type)]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown edge_type: {edge_type}")
    neighbors = engine.graph.get_neighbors(node_id, edge_types=et, direction=direction)
    return {"neighbors": neighbors, "count": len(neighbors)}


# ─────────────────────────────────────────────────────────────────────────────
# Edge endpoints
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/edges")
def get_edges(
    repo_id: Optional[str] = None,
    edge_type: Optional[str] = None,
    limit: int = Query(default=1000, le=5000),
    offset: int = 0,
):
    """List edges with optional repo and type filtering."""
    engine = get_engine()
    et = None
    if edge_type:
        try:
            et = EdgeType(edge_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown edge_type: {edge_type}")
    edges = engine.graph.get_all_edges(repo_id=repo_id, edge_type=et, limit=limit, offset=offset)
    return {"edges": edges, "count": len(edges), "offset": offset}


# ─────────────────────────────────────────────────────────────────────────────
# Traversal
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/traverse", response_model=List[TraversalStep])
def traverse_graph(request: TraversalRequest):
    """BFS traversal from a starting node."""
    engine = get_engine()
    if not engine.graph.has_node(request.start_node_id):
        raise HTTPException(status_code=404, detail="Start node not found.")

    edge_types = None
    if request.edge_types:
        try:
            edge_types = [EdgeType(e) for e in request.edge_types]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid edge type: {exc}")

    steps = engine.graph.traverse_bfs(
        start_id=request.start_node_id,
        max_depth=request.max_depth,
        edge_types=edge_types,
        max_nodes=request.max_nodes,
    )
    return steps


# ─────────────────────────────────────────────────────────────────────────────
# Stats & search
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/stats")
def get_graph_stats(repo_id: Optional[str] = None):
    """Return overall or per-repository graph statistics."""
    engine = get_engine()
    stats = engine.get_stats(repo_id=repo_id)
    return stats.model_dump()


@router.get("/search")
def search_nodes(
    query: str,
    repo_id: Optional[str] = None,
    limit: int = 50,
):
    """Name-contains search across all nodes."""
    engine = get_engine()
    results = engine.graph.search_nodes_by_name(query, repo_id=repo_id)
    return {"results": results[:limit], "count": len(results[:limit])}


# ─────────────────────────────────────────────────────────────────────────────
# Legacy repo-scoped endpoints (keep for backwards compat)
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/{repo_id}/nodes")
def get_nodes_for_repo(
    repo_id: str,
    node_type: Optional[str] = None,
    limit: int = Query(default=500, le=2000),
    offset: int = 0,
):
    engine = get_engine()
    if not engine.graph.has_node(repo_id):
        raise HTTPException(status_code=404, detail="Repository not found.")
    nt = None
    if node_type:
        try:
            nt = NodeType(node_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown node_type: {node_type}")
    nodes = engine.graph.get_all_nodes(repo_id=repo_id, node_type=nt, limit=limit, offset=offset)
    return {"nodes": nodes, "count": len(nodes), "offset": offset}


@router.get("/{repo_id}/edges")
def get_edges_for_repo(
    repo_id: str,
    edge_type: Optional[str] = None,
    limit: int = Query(default=1000, le=5000),
    offset: int = 0,
):
    engine = get_engine()
    if not engine.graph.has_node(repo_id):
        raise HTTPException(status_code=404, detail="Repository not found.")
    et = None
    if edge_type:
        try:
            et = EdgeType(edge_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown edge_type: {edge_type}")
    edges = engine.graph.get_all_edges(repo_id=repo_id, edge_type=et, limit=limit, offset=offset)
    return {"edges": edges, "count": len(edges), "offset": offset}


@router.post("/{repo_id}/traverse", response_model=List[TraversalStep])
def traverse_graph_scoped(repo_id: str, request: TraversalRequest):
    engine = get_engine()
    if not engine.graph.has_node(repo_id):
        raise HTTPException(status_code=404, detail="Repository not found.")
    edge_types = None
    if request.edge_types:
        try:
            edge_types = [EdgeType(e) for e in request.edge_types]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    steps = engine.graph.traverse_bfs(
        start_id=request.start_node_id,
        max_depth=request.max_depth,
        edge_types=edge_types,
        max_nodes=request.max_nodes,
    )
    return steps


@router.get("/{repo_id}/search")
def search_nodes_scoped(repo_id: str, q: str, limit: int = 50):
    engine = get_engine()
    results = engine.graph.search_nodes_by_name(q, repo_id=repo_id)
    return {"results": results[:limit], "count": len(results)}
