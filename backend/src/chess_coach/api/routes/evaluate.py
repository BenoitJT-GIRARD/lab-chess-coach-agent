"""Position evaluation route (Stockfish)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from chess_coach.api.dependencies import get_stockfish_service
from chess_coach.api.schemas import EvaluationResponse
from chess_coach.services.chess_position import is_valid_fen
from chess_coach.services.stockfish_engine import StockfishService, StockfishServiceError

router = APIRouter(tags=["engine"])


@router.get("/evaluate/{fen:path}", response_model=EvaluationResponse, summary="Engine evaluation")
def evaluate_position(
    fen: str,
    stockfish: Annotated[StockfishService, Depends(get_stockfish_service)],
) -> EvaluationResponse:
    """Return Stockfish's evaluation and best move for ``fen``."""

    if not is_valid_fen(fen):
        raise HTTPException(status_code=422, detail=f"Invalid FEN: {fen!r}")

    try:
        result = stockfish.evaluate(fen)
    except StockfishServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return EvaluationResponse(
        fen=result.fen,
        evaluation_type=result.evaluation_type,
        value=result.value,
        best_move=result.best_move,
        best_move_san=result.best_move_san,
        depth=result.depth,
    )
