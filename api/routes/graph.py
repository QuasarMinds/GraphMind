"""Graph query and traversal routes."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.main import get_engine
from graphmind.models import EdgeType, NodeType

router = APIRouter()


class TraversalRequest(BaseModel):
    start_node_id: str
    max_depth: int = 3
    edge_types: Optional[List[str]] = None
    max_nodes: int = 100


class TraversalStep(BaseModel):
    node: dict
    depth: int
    parent_id: Optional[str]
    via_edge_type: Optional[str]


@router.get("/{repo_id}/nodes")
def get_nodes(
    repo_id: str,
    node_type: Optional[str] = None,
    limit: int = Query(default=500, le=2000),
    offset: int = 0,
):
    engine = get_engine()
    if not engine.graph.has_node(repo_id):
        raise HTTPException(status_code=404, detail="Repository not found.")

    nt = NodeType(node_type) if node_type else None
    nodes = engine.graph.get_all_nodes(repo_id=repo_id, node_type=nt, limit=limit, offset=offset)
    return {"nodes": nodes, "count": len(nodes), "offset": offset}


@router.get("/{repo_id}/edges")
def get_edges(
    repo_id: str,
    edge_type: Optional[str] = None,
    limit: int = Query(default=1000, le=5000),
    offset: int = 0,
):
    engine = get_engine()
    if not engine.graph.has_node(repo_id):
        raise HTTPException(status_code=404, detail="Repository not found.")

    et = EdgeType(edge_type) if edge_type else None
    edges = engine.graph.get_all_edges(repo_id=repo_id, edge_type=et, limit=limit, offset=offset)
    return {"edges": edges, "count": len(edges), "offset": offset}


@router.get("/{repo_id}/node/{node_id}")
def get_node_detail(repo_id: str, node_id: str):
    engine = get_engine()
    node = engine.graph.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found.")
    neighbors = engine.graph.get_neighbors(node_id)
    return {"node": {**node, "id": node_id}, "neighbors": neighbors}


@router.post("/{repo_id}/traverse", response_model=List[TraversalStep])
def traverse_graph(repo_id: str, request: TraversalRequest):
    engine = get_engine()
    if not engine.graph.has_node(repo_id):
        raise HTTPException(status_code=404, detail="Repository not found.")

    edge_types = None
    if request.edge_types:
        try:
            edge_types = [EdgeType(e) for e in request.edge_types]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid edge type: {e}")

    steps = engine.graph.traverse_bfs(
        start_id=request.start_node_id,
        max_depth=request.max_depth,
        edge_types=edge_types,
        max_nodes=request.max_nodes,
    )
    return steps


@router.get("/{repo_id}/search")
def search_nodes(repo_id: str, q: str, limit: int = 50):
    engine = get_engine()
    results = engine.graph.search_nodes_by_name(q, repo_id=repo_id)
    return {"results": results[:limit], "count": len(results)}
