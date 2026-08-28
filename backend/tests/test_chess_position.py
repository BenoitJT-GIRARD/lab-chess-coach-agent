"""Tests for the chess position service."""

from __future__ import annotations

import pytest

from chess_coach.services.chess_position import (
    STARTING_FEN,
    InvalidFenError,
    describe_position,
    is_valid_fen,
    uci_to_san,
)


def test_is_valid_fen_accepts_starting_position() -> None:
    assert is_valid_fen(STARTING_FEN) is True


def test_is_valid_fen_rejects_garbage() -> None:
    assert is_valid_fen("not a fen") is False


def test_describe_starting_position() -> None:
    info = describe_position(STARTING_FEN)

    assert info.side_to_move == "white"
    assert info.fullmove_number == 1
    assert info.is_game_over is False
    # There are exactly 20 legal moves from the starting position.
    assert len(info.legal_moves_san) == 20
    assert "e4" in info.legal_moves_san
    assert info.board_ascii  # non-empty diagram


def test_parse_board_raises_on_invalid_fen() -> None:
    with pytest.raises(InvalidFenError):
        describe_position("8/8/8/8/8/8/8/8 w - - 0 1 garbage")


def test_uci_to_san_translates_legal_move() -> None:
    assert uci_to_san(STARTING_FEN, "e2e4") == "e4"


def test_uci_to_san_falls_back_on_illegal_move() -> None:
    # e2e5 is not a legal first move; the raw UCI is returned unchanged.
    assert uci_to_san(STARTING_FEN, "e2e5") == "e2e5"
