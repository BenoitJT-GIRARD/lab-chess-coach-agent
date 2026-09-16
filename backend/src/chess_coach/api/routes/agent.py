"""Agent route: run the full LangGraph workflow for a position."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from chess_coach.agent.graph import ChessAgent
from chess_coach.api.dependencies import get_chess_agent
from chess_coach.api.mapping import agent_answer
from chess_coach.api.schemas import AgentRequest, AgentResponse
from chess_coach.services.chess_position import is_valid_fen

router = APIRouter(tags=["agent"])


@router.post("/agent", response_model=AgentResponse, summary="Run the coaching agent")
def run_agent(
    request: AgentRequest,
    agent: Annotated[ChessAgent, Depends(get_chess_agent)],
) -> AgentResponse:
    """Analyse a position end-to-end through the LangGraph agent."""

    if not is_valid_fen(request.fen):
        raise HTTPException(status_code=422, detail=f"Invalid FEN: {request.fen!r}")

    state = agent.run(request.fen)
    return agent_answer(request.fen, state)
