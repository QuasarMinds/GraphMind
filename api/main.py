"""
GraphMind FastAPI Application
================================
Creates the FastAPI app with CORS, lifespan management,
and route registration.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from graphmind.config import settings
from graphmind.engine import GraphMindEngine

logger = logging.getLogger(__name__)

# Module-level engine instance (shared across all requests)
_engine: GraphMindEngine | None = None


def get_engine() -> GraphMindEngine:
    global _engine
    if _engine is None:
        _engine = GraphMindEngine()
    return _engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle — initialize engine on startup."""
    logger.info("GraphMind API starting...")
    get_engine()
    logger.info("Engine ready.")
    yield
    logger.info("GraphMind API shutting down.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="GraphMind API",
        description="Repository Intelligence and Context Optimization Engine",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    from api.routes import graph, repositories, retrieval, status

    app.include_router(status.router, prefix="/api/v1", tags=["Status"])
    app.include_router(repositories.router, prefix="/api/v1/repositories", tags=["Repositories"])
    app.include_router(graph.router, prefix="/api/v1/graph", tags=["Graph"])
    app.include_router(retrieval.router, prefix="/api/v1/retrieval", tags=["Retrieval"])

    return app


app = create_app()
