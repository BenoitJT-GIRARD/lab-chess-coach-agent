"""Theoretical moves route (Lichess Opening Explorer + local opening book)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from chess_coach.api.dependencies import get_theory_service
from chess_coach.api.schemas import MovesResponse, MoveStat
from chess_coach.services.chess_position import is_valid_fen
from chess_coach.services.lichess import LichessServiceError
from chess_coach.services.theory import TheoryService

router = APIRouter(tags=["theory"])


@router.get("/moves/{fen:path}", response_model=MovesResponse, summary="Theoretical moves")
def get_moves(
    fen: str,
    theory: Annotated[TheoryService, Depends(get_theory_service)],
) -> MovesResponse:
    """Return the theoretical moves available from ``fen``."""

    if not is_valid_fen(fen):
        raise HTTPException(status_code=422, detail=f"Invalid FEN: {fen!r}")

    try:
        result = theory.get_theoretical_moves(fen)
    except LichessServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return MovesResponse(
        fen=result.fen,
        opening_name=result.opening_name,
        opening_eco=result.opening_eco,
        total_games=result.total_games,
        in_theory=result.in_theory,
        moves=[
            MoveStat(
                uci=move.uci,
                san=move.san,
                white=move.white,
                draws=move.draws,
                black=move.black,
                total=move.total,
                source=move.source,
            )
            for move in result.moves
        ],
    )
