"""Retrieval routes (Phase 1 — keyword only stub)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from api.main import get_engine

router = APIRouter()


class RetrievalRequest(BaseModel):
    query: str
    repo_id: str
    top_k: int = 20
    methods: List[str] = ["keyword"]


@router.post("/query")
def query_retrieval(request: RetrievalRequest):
    engine = get_engine()
    if not engine.graph.has_node(request.repo_id):
        raise HTTPException(status_code=404, detail="Repository not found.")

    results = engine.retrieve(request.query, request.repo_id, top_k=request.top_k)
    return {
        "query": request.query,
        "repo_id": request.repo_id,
        "methods_used": request.methods,
        "results": results,
        "count": len(results),
        "note": "Phase 1: keyword retrieval only. Hybrid retrieval implemented in Phase 4.",
    }


@router.get("/methods")
def list_methods():
    return {
        "available": ["keyword"],
        "planned": ["semantic", "symbol", "graph", "hybrid"],
        "phase": 1,
    }
