"""Tests for the local opening book."""

from __future__ import annotations

import chess

from chess_coach.services.chess_position import STARTING_FEN
from chess_coach.services.opening_book import OpeningBook


def _fen_after(*moves_san: str) -> str:
    board = chess.Board()
    for san in moves_san:
        board.push_san(san)
    return board.fen()


def test_starting_position_offers_main_first_moves() -> None:
    result = OpeningBook.lookup(STARTING_FEN)

    assert result is not None
    sans = {move.san for move in result.moves}
    assert {"e4", "d4", "c4", "Nf3"} <= sans
    assert all(move.source == "book" for move in result.moves)


def test_transposition_after_1e4_e5_2nf3_nc6() -> None:
    # This position is shared by the Italian, Ruy Lopez and Scotch lines.
    result = OpeningBook.lookup(_fen_after("e4", "e5", "Nf3", "Nc6"))

    assert result is not None
    sans = {move.san for move in result.moves}
    assert {"Bc4", "Bb5", "d4"} <= sans


def test_unknown_position_returns_none() -> None:
    # 1.a4 is not part of any curated line.
    assert OpeningBook.lookup(_fen_after("a4")) is None
