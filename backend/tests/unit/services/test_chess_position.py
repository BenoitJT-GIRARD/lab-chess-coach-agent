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


def test_a_position_no_game_can_reach_is_not_a_valid_fen() -> None:
    """Eight white kings parse. They do not play, and the coach must not answer about them.

    `chess.Board` is a parser: it builds a board out of any well-formed FEN and says nothing
    about whether the position is legal. A coach that accepts one looks up an opening that
    cannot exist and returns an engine score for it, with a 200.
    """
    assert is_valid_fen("8/8/8/8/8/8/8/KKKKKKKK w - - 0 1") is False


def test_an_impossible_position_is_refused_with_what_is_wrong_with_it() -> None:
    """The message carries the diagnosis, not just the string that was refused."""
    with pytest.raises(InvalidFenError) as refusal:
        describe_position("8/8/8/8/8/8/8/KKKKKKKK w - - 0 1")

    assert "Status" in str(refusal.value)


def test_a_bare_kings_endgame_is_a_legal_position() -> None:
    """The tightening must not refuse a real position: two kings alone is a drawn game."""
    info = describe_position("8/8/8/8/8/8/8/K6k w - - 0 1")

    assert info.is_game_over is True
