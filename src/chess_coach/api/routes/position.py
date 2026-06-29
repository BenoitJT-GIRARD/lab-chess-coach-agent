"""Position identification route.

Turns a FEN string into a structured description (side to move, legal moves,
board diagram). The Angular frontend uses it to keep its board in sync and the
agent uses the same service internally.
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException

from chess_coach.api.schemas import PositionResponse
from chess_coach.services.chess_position import describe_position, is_valid_fen

router = APIRouter(tags=["position"])


@router.get("/position/{fen:path}", response_model=PositionResponse, summary="Describe a FEN")
def get_position(fen: str) -> PositionResponse:
    """Return a structured description of the position encoded by ``fen``."""

    if not is_valid_fen(fen):
        raise HTTPException(status_code=422, detail=f"Invalid FEN: {fen!r}")
    return PositionResponse(**asdict(describe_position(fen)))
