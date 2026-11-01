"""Repository management routes."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from api.main import get_engine

router = APIRouter()


class AddRepositoryRequest(BaseModel):
    path: str
    force_reindex: bool = False


class RepositoryResponse(BaseModel):
    id: str
    name: str
    path: str
    total_files: Optional[int] = None
    language_stats: Optional[dict] = None


class FileTreeItem(BaseModel):
    path: str
    name: str
    type: str  # "file" | "directory"
    language: Optional[str] = None
    size_bytes: Optional[int] = None
    symbol_count: Optional[int] = None
    parse_status: Optional[str] = None


@router.get("", response_model=List[RepositoryResponse])
def list_repositories():
    engine = get_engine()
    repos = engine.list_repositories()
    return [
        RepositoryResponse(
            id=r["id"],
            name=r.get("name", ""),
            path=r.get("path", ""),
            total_files=r.get("total_files"),
            language_stats=r.get("language_stats"),
        )
        for r in repos
    ]


@router.post("", response_model=RepositoryResponse, status_code=201)
async def add_repository(request: AddRepositoryRequest, background_tasks: BackgroundTasks):
    """Add and index a repository. Indexing runs synchronously for now (Phase 3 will add WS streaming)."""
    engine = get_engine()
    path = Path(request.path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {request.path}")
    if not path.is_dir():
        raise HTTPException(status_code=400, detail="Path must be a directory.")

    try:
        repo_node = engine.index_repository(path, force_reindex=request.force_reindex)
        return RepositoryResponse(
            id=repo_node.id,
            name=repo_node.name,
            path=repo_node.path,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{repo_id}", response_model=RepositoryResponse)
def get_repository(repo_id: str):
    engine = get_engine()
    r = engine.get_repository(repo_id)
    if not r:
        raise HTTPException(status_code=404, detail="Repository not found.")
    return RepositoryResponse(
        id=repo_id,
        name=r.get("name", ""),
        path=r.get("path", ""),
        total_files=r.get("total_files"),
        language_stats=r.get("language_stats"),
    )


@router.get("/{repo_id}/stats")
def get_repo_stats(repo_id: str):
    engine = get_engine()
    if not engine.graph.has_node(repo_id):
        raise HTTPException(status_code=404, detail="Repository not found.")
    stats = engine.get_stats(repo_id)
    return stats.model_dump()


@router.get("/{repo_id}/files", response_model=List[FileTreeItem])
def get_repo_files(repo_id: str, limit: int = 500, offset: int = 0):
    """Return file nodes for the repository."""
    from graphmind.models import NodeType
    engine = get_engine()
    if not engine.graph.has_node(repo_id):
        raise HTTPException(status_code=404, detail="Repository not found.")

    nodes = engine.graph.get_all_nodes(repo_id=repo_id, node_type=NodeType.FILE, limit=limit, offset=offset)
    return [
        FileTreeItem(
            path=n.get("path", ""),
            name=n.get("name", ""),
            type="file",
            language=n.get("language"),
            size_bytes=n.get("size_bytes"),
            symbol_count=n.get("symbol_count"),
            parse_status=n.get("parse_status"),
        )
        for n in nodes
    ]


@router.get("/{repo_id}/progress")
def get_indexing_progress(repo_id: str):
    engine = get_engine()
    prog = engine.get_indexing_progress(repo_id)
    if prog is None:
        raise HTTPException(status_code=404, detail="No indexing progress found.")
    return prog
