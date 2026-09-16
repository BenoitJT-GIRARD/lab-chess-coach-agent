"""FastAPI application factory.

``create_app`` assembles the application from its routers and middleware so the
same builder can be reused by the test suite. ``app`` is the ASGI entry point
imported by uvicorn (``chess_coach.api.main:app``).

**The embedding model is loaded at startup, in a thread.** Left lazy, it loads inside the
first request that needs it: the first player to ask a question waits ten seconds on a warm
cache and considerably longer on a cold one, while every proxy in front of the service counts
that as a timeout. Warming it in the background instead means the service answers its
healthcheck immediately, keeps starting when there is no model to be had, and is ready by the
time anyone has finished setting up a board.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from chess_coach import __version__
from chess_coach.api.routes import (
    agent,
    evaluate,
    health,
    history,
    moves,
    position,
    vector_search,
    videos,
)

API_PREFIX = "/api/v1"

logger = logging.getLogger(__name__)

#: The sentence the warm-up embeds. Its content is irrelevant; what matters is that the call
#: goes all the way through the model, because that is what pays the loading cost.
WARM_UP_QUERY = "chess opening"


def warm_embeddings() -> None:
    """Load the embedding model, and say so. A failure here is logged, never raised."""

    from chess_coach.services.embeddings import EmbeddingService

    try:
        EmbeddingService().embed_one(WARM_UP_QUERY)
    # A warm-up must never stop the service, whatever it ran into.
    except Exception as exc:
        logger.warning("Embedding model not warmed up: %s", exc)
    else:
        logger.info("Embedding model ready")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start the warm-up, serve, and let the thread go when the process stops."""

    thread = threading.Thread(target=warm_embeddings, name="warm-embeddings", daemon=True)
    thread.start()
    yield


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""

    app = FastAPI(
        title="Chess Coach API",
        version=__version__,
        lifespan=lifespan,
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
    app.include_router(history.router, prefix=API_PREFIX)

    return app


app = create_app()
