"""Tests for the LangGraph agent (all services faked)."""

from __future__ import annotations

import chess
from fastapi.testclient import TestClient

from chess_coach.agent.graph import ChessAgent
from chess_coach.agent.state import AgentDeps
from chess_coach.api.dependencies import get_chess_agent
from chess_coach.api.main import create_app
from chess_coach.config import Settings
from chess_coach.services.chess_position import STARTING_FEN
from chess_coach.services.lichess import OpeningExplorerResult, TheoryMove
from chess_coach.services.milvus_store import SearchHit
from chess_coach.services.stockfish_engine import EvaluationResult
from chess_coach.services.youtube import VideoItem


class FakeTheory:
    def __init__(self, *, known: bool) -> None:
        self._known = known

    def get_theoretical_moves(self, fen: str) -> OpeningExplorerResult:
        if not self._known:
            return OpeningExplorerResult(fen, None, None, 0, [])
        return OpeningExplorerResult(
            fen,
            "Italian Game",
            "C50",
            1500,
            [TheoryMove(uci="e2e4", san="e4", white=600, draws=200, black=300, source="book")],
            in_theory=True,
        )


class FakeStockfish:
    def evaluate(self, fen: str) -> EvaluationResult:
        return EvaluationResult(fen, "cp", 35, "e2e4", "e4", 15)


class FakeRag:
    def search(self, query: str, *, top_k: int = 3) -> list[SearchHit]:
        return [SearchHit("Idées de l'ouverture.", "Italian Game", "ouverture-italienne.md", 0.9)]


class FakeYoutube:
    is_configured = True

    def search_videos(self, opening: str, *, max_results: int = 5) -> list[VideoItem]:
        return [VideoItem("vid1", "Tutoriel", "Chaine", "https://youtu.be/vid1", "thumb")]


class FakeMongo:
    def __init__(self) -> None:
        self.saved: list[dict] = []

    def save_interaction(self, document: dict) -> str:
        self.saved.append(document)
        return "fake-id"


def _agent(*, known: bool, mongo: FakeMongo | None = None) -> ChessAgent:
    deps = AgentDeps(
        settings=Settings(youtube_api_key="dummy", llm_enabled=False),
        theory=FakeTheory(known=known),
        stockfish=FakeStockfish(),
        rag=FakeRag(),
        youtube=FakeYoutube(),
        mongo=mongo or FakeMongo(),
    )
    return ChessAgent(deps)


def test_agent_in_theory_skips_engine_and_persists() -> None:
    mongo = FakeMongo()
    state = _agent(known=True, mongo=mongo).run(STARTING_FEN)

    assert state["in_theory"] is True
    assert state["opening_name"] == "Italian Game"
    assert state.get("evaluation") is None  # engine skipped when in theory
    assert "theory" in state["sources_used"]
    assert "rag" in state["sources_used"]
    assert "Italian Game" in state["recommendation"]
    assert mongo.saved and mongo.saved[0]["fen"] == STARTING_FEN


def test_agent_out_of_theory_uses_engine() -> None:
    board = chess.Board()
    board.push_san("a4")  # an off-beat first move, out of the book
    state = _agent(known=False).run(board.fen())

    assert state["in_theory"] is False
    assert state["evaluation"] is not None
    assert "engine" in state["sources_used"]
    assert "Stockfish" in state["recommendation"]


def test_agent_route_maps_state() -> None:
    app = create_app()
    app.dependency_overrides[get_chess_agent] = lambda: _agent(known=True)
    client = TestClient(app)

    response = client.post("/api/v1/agent", json={"fen": STARTING_FEN})

    assert response.status_code == 200
    body = response.json()
    assert body["in_theory"] is True
    assert body["opening_name"] == "Italian Game"
    assert body["videos"][0]["video_id"] == "vid1"
    assert body["recommendation"]
