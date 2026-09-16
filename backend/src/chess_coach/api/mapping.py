"""The agent's final state, mapped onto the models the API publishes.

The mapping lives here rather than in the route because it depends on nothing the route
depends on. `AgentState` is a ``TypedDict`` with ``total=False``: every key is optional, and a
node that fails leaves its key unset. Turning that into a response is a decision about what an
unfinished run looks like from outside — an answer with a hole in it, never a crash and never
an invented default — and it is worth testing without building a graph, loading a model or
opening a socket.

The state arrives as a plain mapping on purpose. `AgentState` is declared beside the services
it carries, so importing it would drag the embedding stack into anything that reads this file.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from chess_coach.api.schemas import (
    AgentResponse,
    EvaluationResponse,
    MoveStat,
    Passage,
    ReferenceGame,
    VideoResult,
)


def agent_answer(fen: str, state: Mapping[str, Any]) -> AgentResponse:
    """Build the published answer for ``fen`` from the state the graph left behind."""

    evaluation = state.get("evaluation")
    return AgentResponse(
        fen=fen,
        valid=state.get("valid", False),
        opening_name=state.get("opening_name"),
        opening_eco=state.get("opening_eco"),
        in_theory=state.get("in_theory", False),
        total_games=state.get("total_games", 0),
        theory_moves=[MoveStat(**move) for move in state.get("theory_moves", [])],
        reference_games=[ReferenceGame(**game) for game in state.get("reference_games", [])],
        evaluation=EvaluationResponse(**evaluation) if evaluation else None,
        passages=[Passage(**passage) for passage in state.get("passages", [])],
        videos=[VideoResult(**video) for video in state.get("videos", [])],
        opening_summary=state.get("opening_summary", ""),
        recommendation=state.get("recommendation", ""),
        sources_used=state.get("sources_used", []),
        error=state.get("error"),
    )
