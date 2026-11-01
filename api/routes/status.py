"""Status and health-check routes."""

from fastapi import APIRouter
from pydantic import BaseModel

from api.main import get_engine
from graphmind.config import settings

router = APIRouter()


class StatusResponse(BaseModel):
    status: str
    version: str
    node_count: int
    edge_count: int
    repositories: int
    tree_sitter_available: bool
    api_version: str = "v1"


@router.get("/status", response_model=StatusResponse)
def get_status() -> StatusResponse:
    engine = get_engine()
    from graphmind.parser.parser import _TREE_SITTER_AVAILABLE
    repos = engine.list_repositories()
    return StatusResponse(
        status="ok",
        version="0.1.0",
        node_count=engine.graph.node_count(),
        edge_count=engine.graph.edge_count(),
        repositories=len(repos),
        tree_sitter_available=_TREE_SITTER_AVAILABLE,
    )
