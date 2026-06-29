"""Tests for the Lichess Opening Explorer client (HTTP mocked with respx)."""

from __future__ import annotations

import httpx
import pytest
import respx

from chess_coach.config import Settings
from chess_coach.services.chess_position import STARTING_FEN
from chess_coach.services.lichess import LichessService, LichessServiceError

EXPLORER_URL = "https://explorer.lichess.ovh/lichess"

SAMPLE_PAYLOAD = {
    "white": 1000,
    "draws": 400,
    "black": 600,
    "opening": {"eco": "B00", "name": "King's Pawn Game"},
    "moves": [
        {"uci": "e2e4", "san": "e4", "white": 600, "draws": 200, "black": 300},
        {"uci": "d2d4", "san": "d4", "white": 300, "draws": 150, "black": 250},
    ],
}


@pytest.fixture
def service() -> LichessService:
    # Short timeout keeps the (mocked) tests fast and deterministic.
    return LichessService(settings=Settings(http_timeout=2.0))


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
def test_rate_limit_raises_service_error(service: LichessService) -> None:
    respx.get(EXPLORER_URL).mock(return_value=httpx.Response(429))

    with pytest.raises(LichessServiceError, match="429"):
        service.get_theoretical_moves(STARTING_FEN)


@respx.mock
def test_timeout_raises_service_error(service: LichessService) -> None:
    respx.get(EXPLORER_URL).mock(side_effect=httpx.TimeoutException("timeout"))

    with pytest.raises(LichessServiceError, match="timed out"):
        service.get_theoretical_moves(STARTING_FEN)
