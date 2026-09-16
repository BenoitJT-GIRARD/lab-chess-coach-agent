"""Tests for the position, moves and evaluate routes (services overridden)."""

from __future__ import annotations

from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from chess_coach.api.dependencies import get_stockfish_service, get_theory_service
from chess_coach.api.main import create_app
from chess_coach.services.chess_position import STARTING_FEN
from chess_coach.services.lichess import OpeningExplorerResult, ReferenceGame, TheoryMove
from chess_coach.services.stockfish_engine import EvaluationResult

pytestmark = pytest.mark.integration


def _path(prefix: str, fen: str) -> str:
    # Encode the FEN but keep the slashes, which the `{fen:path}` converter reads.
    return f"{prefix}/{quote(fen, safe='/')}"


class FakeTheory:
    def get_theoretical_moves(self, fen: str) -> OpeningExplorerResult:
        return OpeningExplorerResult(
            fen=fen,
            opening_name="King's Pawn Game",
            opening_eco="B00",
            total_games=1500,
            moves=[TheoryMove(uci="e2e4", san="e4", white=600, draws=200, black=300)],
            in_theory=True,
            reference_games=[
                ReferenceGame(
                    game_id="abc123",
                    white="Carlsen",
                    black="Nakamura",
                    white_rating=2850,
                    black_rating=2780,
                    winner="white",
                    year=2023,
                )
            ],
        )


class FakeStockfish:
    def evaluate(self, fen: str) -> EvaluationResult:
        return EvaluationResult(
            fen=fen,
            evaluation_type="cp",
            value=34,
            best_move="e2e4",
            best_move_san="e4",
            depth=15,
        )


def _client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_theory_service] = FakeTheory
    app.dependency_overrides[get_stockfish_service] = FakeStockfish
    return TestClient(app)


def test_position_route_describes_fen() -> None:
    response = _client().get(_path("/api/v1/position", STARTING_FEN))

    assert response.status_code == 200
    assert response.json()["side_to_move"] == "white"


def test_position_route_rejects_invalid_fen() -> None:
    response = _client().get("/api/v1/position/not-a-fen")

    assert response.status_code == 422


def test_moves_route_returns_theory() -> None:
    response = _client().get(_path("/api/v1/moves", STARTING_FEN))

    assert response.status_code == 200
    body = response.json()
    assert body["in_theory"] is True
    assert body["opening_name"] == "King's Pawn Game"
    assert body["moves"][0]["san"] == "e4"


def test_moves_route_lists_the_reference_games() -> None:
    response = _client().get(_path("/api/v1/moves", STARTING_FEN))

    game = response.json()["reference_games"][0]
    assert game["white"] == "Carlsen"
    assert game["result"] == "1-0"
    assert game["url"] == "https://lichess.org/abc123"


def test_evaluate_route_returns_score() -> None:
    response = _client().get(_path("/api/v1/evaluate", STARTING_FEN))

    assert response.status_code == 200
    body = response.json()
    assert body["evaluation_type"] == "cp"
    assert body["best_move_san"] == "e4"
