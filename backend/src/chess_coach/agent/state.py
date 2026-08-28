"""Shared state and dependency container for the agent graph.

``AgentState`` is the dictionary that flows through the LangGraph nodes; every
node reads from it and returns a partial update. ``AgentDeps`` bundles the
services the nodes rely on, which makes the graph easy to test with fakes.
"""

from __future__ import annotations

from dataclasses import dataclass
from operator import add
from typing import Annotated, Any, TypedDict

from chess_coach.config import Settings
from chess_coach.services.mongo import MongoService
from chess_coach.services.rag_search import RagService
from chess_coach.services.stockfish_engine import StockfishService
from chess_coach.services.theory import TheoryService
from chess_coach.services.youtube import YoutubeService


class AgentState(TypedDict, total=False):
    """State passed between the agent's nodes."""

    fen: str
    valid: bool
    position: dict[str, Any]
    opening_name: str | None
    opening_eco: str | None
    in_theory: bool
    theory_moves: list[dict[str, Any]]
    reference_games: list[dict[str, Any]]
    evaluation: dict[str, Any] | None
    passages: list[dict[str, Any]]
    videos: list[dict[str, Any]]
    recommendation: str
    # Reducer: each node appends the tools it used; the lists are concatenated.
    sources_used: Annotated[list[str], add]
    error: str | None


@dataclass(slots=True)
class AgentDeps:
    """The services the agent nodes depend on."""

    settings: Settings
    theory: TheoryService
    stockfish: StockfishService
    rag: RagService
    youtube: YoutubeService
    mongo: MongoService
