"""FastAPI dependency providers.

Exposing the services through dependencies lets the routes stay declarative and,
crucially, lets the test suite swap a real service for a fake one via
``app.dependency_overrides``.
"""

from __future__ import annotations

from chess_coach.services.rag_search import RagService
from chess_coach.services.stockfish_engine import StockfishService
from chess_coach.services.theory import TheoryService


def get_theory_service() -> TheoryService:
    """Provide a :class:`TheoryService` (Lichess + local opening book)."""

    return TheoryService()


def get_rag_service() -> RagService:
    """Provide a :class:`RagService` (embeddings + Milvus search)."""

    return RagService()


def get_stockfish_service() -> StockfishService:
    """Provide a :class:`StockfishService` instance."""

    return StockfishService()
