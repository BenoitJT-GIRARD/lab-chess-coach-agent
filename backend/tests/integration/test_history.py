"""Tests for the history route (MongoDB replaced by a fake)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from chess_coach.api.dependencies import get_mongo_service
from chess_coach.api.main import create_app

pytestmark = pytest.mark.integration

INTERACTIONS = [
    {
        "fen": "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
        "opening_name": "Sicilian Defense",
        "in_theory": True,
        "sources_used": ["theory", "rag", "llm"],
        "created_at": "2026-09-02T09:30:00+00:00",
    },
    {
        "fen": "rnbqkbnr/pppp1ppp/8/4p2Q/4P3/8/PPPP1PPP/RNB1KBNR b KQkq - 1 2",
        "opening_name": None,
        "in_theory": False,
        "sources_used": ["engine", "rag"],
        "created_at": "2026-09-02T09:20:00+00:00",
    },
]


class FakeMongo:
    def __init__(self) -> None:
        self.limit_recu: int | None = None

    def recent_interactions(self, limit: int = 10) -> list[dict]:
        self.limit_recu = limit
        return INTERACTIONS[:limit]

    def count_interactions(self) -> int:
        return 42


def _client(mongo: FakeMongo) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_mongo_service] = lambda: mongo
    return TestClient(app)


def test_history_returns_the_recent_interactions() -> None:
    response = _client(FakeMongo()).get("/api/v1/history")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 42
    assert len(body["interactions"]) == 2
    assert body["interactions"][0]["opening_name"] == "Sicilian Defense"
    assert body["interactions"][1]["in_theory"] is False
    assert body["interactions"][1]["sources_used"] == ["engine", "rag"]


def test_history_honours_the_limit() -> None:
    mongo = FakeMongo()

    response = _client(mongo).get("/api/v1/history", params={"limit": 1})

    assert mongo.limit_recu == 1
    assert len(response.json()["interactions"]) == 1


def test_history_rejects_an_out_of_range_limit() -> None:
    response = _client(FakeMongo()).get("/api/v1/history", params={"limit": 500})

    assert response.status_code == 422
