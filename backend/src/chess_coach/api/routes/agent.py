"""Agent route: run the full LangGraph workflow for a position."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from chess_coach.agent.graph import ChessAgent
from chess_coach.agent.state import AgentState
from chess_coach.api.dependencies import get_chess_agent
from chess_coach.api.schemas import (
    AgentRequest,
    AgentResponse,
    EvaluationResponse,
    MoveStat,
    Passage,
    ReferenceGame,
    VideoResult,
)
from chess_coach.services.chess_position import is_valid_fen

router = APIRouter(tags=["agent"])


def _to_response(fen: str, state: AgentState) -> AgentResponse:
    """Map the agent's final state onto the API response model."""

    evaluation = state.get("evaluation")
    return AgentResponse(
        fen=fen,
        valid=state.get("valid", False),
        opening_name=state.get("opening_name"),
        opening_eco=state.get("opening_eco"),
        in_theory=state.get("in_theory", False),
        theory_moves=[MoveStat(**move) for move in state.get("theory_moves", [])],
        reference_games=[ReferenceGame(**game) for game in state.get("reference_games", [])],
        evaluation=EvaluationResponse(**evaluation) if evaluation else None,
        passages=[Passage(**passage) for passage in state.get("passages", [])],
        videos=[VideoResult(**video) for video in state.get("videos", [])],
        recommendation=state.get("recommendation", ""),
        sources_used=state.get("sources_used", []),
        error=state.get("error"),
    )


@router.post("/agent", response_model=AgentResponse, summary="Run the coaching agent")
def run_agent(
    request: AgentRequest,
    agent: Annotated[ChessAgent, Depends(get_chess_agent)],
) -> AgentResponse:
    """Analyse a position end-to-end through the LangGraph agent."""

    if not is_valid_fen(request.fen):
        raise HTTPException(status_code=422, detail=f"Invalid FEN: {request.fen!r}")

    state = agent.run(request.fen)
    return _to_response(request.fen, state)
