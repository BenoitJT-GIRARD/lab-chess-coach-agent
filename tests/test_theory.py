"""Tests for the combined theory service (book + Lichess fallback logic)."""

from __future__ import annotations

import chess

from chess_coach.config import Settings
from chess_coach.services.chess_position import STARTING_FEN
from chess_coach.services.theory import TheoryService


def test_without_token_uses_local_book() -> None:
    # No Lichess token configured: theory must come from the local book.
    service = TheoryService(settings=Settings(lichess_token=""))

    result = service.get_theoretical_moves(STARTING_FEN)

    assert result.in_theory is True
    assert {move.san for move in result.moves} >= {"e4", "d4"}


def test_unknown_position_is_out_of_theory() -> None:
    board = chess.Board()
    board.push_san("a4")
    service = TheoryService(settings=Settings(lichess_token=""))

    result = service.get_theoretical_moves(board.fen())

    assert result.in_theory is False
    assert result.moves == []
