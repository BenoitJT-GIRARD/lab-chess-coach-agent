"""Tests for the combined theory service (book + Lichess fallback logic)."""

from __future__ import annotations

import chess

from chess_coach.config import Settings
from chess_coach.services.chess_position import STARTING_FEN
from chess_coach.services.lichess import OpeningExplorerResult, ReferenceGame, TheoryMove
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


class FakeLichess:
    """Stands in for the Explorer, so the tests never touch the network."""

    is_configured = True

    def __init__(self, result: OpeningExplorerResult) -> None:
        self.result = result
        self.calls = 0

    def get_theoretical_moves(self, fen: str) -> OpeningExplorerResult:
        self.calls += 1
        return self.result


def test_lichess_is_preferred_when_it_knows_the_position() -> None:
    lichess = FakeLichess(
        OpeningExplorerResult(
            fen=STARTING_FEN,
            opening_name="Italian Game",
            opening_eco="C50",
            total_games=48726,
            moves=[TheoryMove(uci="e2e4", san="e4", white=1, draws=1, black=1)],
            in_theory=True,
            reference_games=[ReferenceGame("g1", "Carlsen", "Caruana", 2850, 2820, "draw", 2021)],
        )
    )
    service = TheoryService(settings=Settings(lichess_token="lip_test"), lichess=lichess)

    result = service.get_theoretical_moves(STARTING_FEN)

    assert lichess.calls == 1
    assert result.opening_name == "Italian Game"
    assert result.reference_games[0].result == "1/2-1/2"


def test_the_local_book_takes_over_when_lichess_finds_nothing() -> None:
    lichess = FakeLichess(
        OpeningExplorerResult(
            fen=STARTING_FEN,
            opening_name=None,
            opening_eco=None,
            total_games=12,
            moves=[],
            in_theory=False,
        )
    )
    service = TheoryService(settings=Settings(lichess_token="lip_test"), lichess=lichess)

    result = service.get_theoretical_moves(STARTING_FEN)

    assert result.in_theory is True
    assert {move.san for move in result.moves} >= {"e4", "d4"}
    assert all(move.source == "book" for move in result.moves)
