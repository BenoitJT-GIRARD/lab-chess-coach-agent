"""FastAPI application factory.

``create_app`` assembles the application from its routers and middleware so the
same builder can be reused by the test suite. ``app`` is the ASGI entry point
imported by uvicorn (``chess_coach.api.main:app``).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from chess_coach import __version__
from chess_coach.api.routes import (
    agent,
    evaluate,
    health,
    moves,
    position,
    vector_search,
    videos,
)

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""

    app = FastAPI(
        title="Chess Coach API",
        version=__version__,
        description=(
            "Chess-opening coaching agent for club players. Exposes the LangGraph "
            "agent and its underlying tools (Lichess theory, Stockfish "
            "evaluation, Milvus RAG, YouTube videos)."
        ),
    )

    # The Angular frontend (http://localhost:4200) calls this API from the
    # browser, so cross-origin requests must be allowed.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:4200"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix=API_PREFIX)
    app.include_router(position.router, prefix=API_PREFIX)
    app.include_router(moves.router, prefix=API_PREFIX)
    app.include_router(evaluate.router, prefix=API_PREFIX)
    app.include_router(vector_search.router, prefix=API_PREFIX)
    app.include_router(videos.router, prefix=API_PREFIX)
    app.include_router(agent.router, prefix=API_PREFIX)

    return app


app = create_app()
