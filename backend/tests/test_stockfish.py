"""Tests for the Stockfish service (engine faked, no binary required)."""

from __future__ import annotations

import pytest

from chess_coach.services.chess_position import STARTING_FEN
from chess_coach.services.stockfish_engine import StockfishService, StockfishServiceError


class FakeEngine:
    """Minimal stand-in for the ``stockfish.Stockfish`` engine."""

    def __init__(self, *, valid: bool = True) -> None:
        self._valid = valid

    def is_fen_valid(self, fen: str) -> bool:
        return self._valid

    def set_fen_position(self, fen: str) -> None:
        self._fen = fen

    def get_evaluation(self) -> dict:
        return {"type": "cp", "value": 34}

    def get_best_move(self) -> str:
        return "e2e4"


def test_evaluate_returns_score_and_best_move() -> None:
    service = StockfishService(engine=FakeEngine())

    result = service.evaluate(STARTING_FEN)

    assert result.evaluation_type == "cp"
    assert result.value == 34
    assert result.best_move == "e2e4"
    assert result.best_move_san == "e4"


def test_evaluate_rejects_invalid_fen() -> None:
    service = StockfishService(engine=FakeEngine(valid=False))

    with pytest.raises(StockfishServiceError):
        service.evaluate(STARTING_FEN)
