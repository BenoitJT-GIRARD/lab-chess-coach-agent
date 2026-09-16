"""Tests for the Lichess Opening Explorer client (HTTP mocked with respx)."""

from __future__ import annotations

import httpx
import pytest
import respx

from chess_coach.config import Settings
from chess_coach.services.chess_position import STARTING_FEN
from chess_coach.services.lichess import LichessService, LichessServiceError

pytestmark = pytest.mark.integration

# The client queries the master database: those are the reference games.
EXPLORER_URL = "https://explorer.lichess.ovh/masters"

SAMPLE_PAYLOAD = {
    "white": 1000,
    "draws": 400,
    "black": 600,
    "opening": {"eco": "B00", "name": "King's Pawn Game"},
    "moves": [
        {"uci": "e2e4", "san": "e4", "white": 600, "draws": 200, "black": 300},
        {"uci": "d2d4", "san": "d4", "white": 300, "draws": 150, "black": 250},
    ],
    "topGames": [
        {
            "id": "abc123",
            "winner": "white",
            "white": {"name": "Carlsen", "rating": 2850},
            "black": {"name": "Nakamura", "rating": 2780},
            "year": 2023,
        }
    ],
}

# Same shape, but a position only a handful of games ever reached.
RARE_PAYLOAD = {
    "white": 20,
    "draws": 8,
    "black": 20,
    "opening": {"eco": "C20", "name": "Wayward Queen Attack"},
    "moves": [{"uci": "b8c6", "san": "Nc6", "white": 18, "draws": 7, "black": 18}],
    "topGames": [],
}


@pytest.fixture
def service() -> LichessService:
    # Short timeout keeps the (mocked) tests fast and deterministic.
    return LichessService(settings=Settings(http_timeout=2.0, theory_min_games=1000))


@respx.mock
def test_get_theoretical_moves_parses_payload(service: LichessService) -> None:
    respx.get(EXPLORER_URL).mock(return_value=httpx.Response(200, json=SAMPLE_PAYLOAD))

    result = service.get_theoretical_moves(STARTING_FEN)

    assert result.in_theory is True
    assert result.opening_name == "King's Pawn Game"
    assert result.opening_eco == "B00"
    assert result.total_games == 2000
    assert [move.san for move in result.moves] == ["e4", "d4"]
    assert result.moves[0].total == 1100


@respx.mock
def test_reference_games_are_parsed(service: LichessService) -> None:
    respx.get(EXPLORER_URL).mock(return_value=httpx.Response(200, json=SAMPLE_PAYLOAD))

    game = service.get_theoretical_moves(STARTING_FEN).reference_games[0]

    assert game.white == "Carlsen"
    assert game.black == "Nakamura"
    assert game.result == "1-0"
    assert game.url == "https://lichess.org/abc123"
    assert game.year == 2023


@respx.mock
def test_a_rarely_played_position_is_out_of_theory(service: LichessService) -> None:
    # The master database answers for almost any legal position. Forty-eight
    # games is a curiosity, not theory: the agent must turn to the engine.
    respx.get(EXPLORER_URL).mock(return_value=httpx.Response(200, json=RARE_PAYLOAD))

    result = service.get_theoretical_moves(STARTING_FEN)

    assert result.total_games == 48
    assert result.in_theory is False


@respx.mock
def test_rate_limit_raises_service_error(service: LichessService) -> None:
    respx.get(EXPLORER_URL).mock(return_value=httpx.Response(429))

    with pytest.raises(LichessServiceError, match="429"):
        service.get_theoretical_moves(STARTING_FEN)


@respx.mock
def test_a_refused_token_raises_service_error(service: LichessService) -> None:
    respx.get(EXPLORER_URL).mock(return_value=httpx.Response(401))

    with pytest.raises(LichessServiceError, match="401"):
        service.get_theoretical_moves(STARTING_FEN)


@respx.mock
def test_timeout_raises_service_error(service: LichessService) -> None:
    respx.get(EXPLORER_URL).mock(side_effect=httpx.TimeoutException("timeout"))

    with pytest.raises(LichessServiceError, match="timed out"):
        service.get_theoretical_moves(STARTING_FEN)
