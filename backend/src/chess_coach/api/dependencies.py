"""FastAPI dependency providers.

Exposing the services through dependencies lets the routes stay declarative and,
crucially, lets the test suite swap a real service for a fake one via
``app.dependency_overrides``.
"""

from __future__ import annotations

from functools import lru_cache

from chess_coach.agent.graph import ChessAgent, build_default_agent
from chess_coach.services.rag_search import RagService
from chess_coach.services.stockfish_engine import StockfishService
from chess_coach.services.theory import TheoryService
from chess_coach.services.youtube import YoutubeService


def get_theory_service() -> TheoryService:
    """Provide a :class:`TheoryService` (Lichess + local opening book)."""

    return TheoryService()


def get_rag_service() -> RagService:
    """Provide a :class:`RagService` (embeddings + Milvus search)."""

    return RagService()


def get_stockfish_service() -> StockfishService:
    """Provide a :class:`StockfishService` instance."""

    return StockfishService()


def get_youtube_service() -> YoutubeService:
    """Provide a :class:`YoutubeService` instance."""

    return YoutubeService()


@lru_cache
def get_chess_agent() -> ChessAgent:
    """Provide the compiled LangGraph agent (built once and reused)."""

    return build_default_agent()
