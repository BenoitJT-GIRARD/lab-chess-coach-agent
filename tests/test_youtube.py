"""Tests for the YouTube service and videos route (API client faked)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from chess_coach.api.dependencies import get_youtube_service
from chess_coach.api.main import create_app
from chess_coach.config import Settings
from chess_coach.services.youtube import YoutubeService

SAMPLE_RESPONSE = {
    "items": [
        {
            "id": {"videoId": "abc123"},
            "snippet": {
                "title": "Italian Game Explained",
                "channelTitle": "ChessChannel",
                "thumbnails": {"medium": {"url": "https://img/abc.jpg"}},
            },
        },
        # An item without a videoId (e.g. a channel) must be ignored.
        {"id": {"kind": "youtube#channel"}, "snippet": {"title": "A channel"}},
    ]
}


class _FakeRequest:
    def __init__(self, response: dict) -> None:
        self._response = response

    def execute(self) -> dict:
        return self._response


class FakeYoutube:
    """Stand-in for the googleapiclient resource (search().list().execute())."""

    def __init__(self, response: dict) -> None:
        self._response = response

    def search(self) -> FakeYoutube:
        return self

    def list(self, **_: object) -> _FakeRequest:
        return _FakeRequest(self._response)


def test_search_videos_parses_and_filters() -> None:
    service = YoutubeService(
        settings=Settings(youtube_api_key="dummy"),
        client=FakeYoutube(SAMPLE_RESPONSE),
    )

    videos = service.search_videos("Ouverture italienne")

    assert len(videos) == 1
    assert videos[0].video_id == "abc123"
    assert videos[0].url == "https://www.youtube.com/watch?v=abc123"
    assert videos[0].channel == "ChessChannel"


def test_videos_route_returns_results() -> None:
    app = create_app()
    app.dependency_overrides[get_youtube_service] = lambda: YoutubeService(
        settings=Settings(youtube_api_key="dummy"),
        client=FakeYoutube(SAMPLE_RESPONSE),
    )
    client = TestClient(app)

    response = client.get("/api/v1/videos/Ouverture italienne")

    assert response.status_code == 200
    assert response.json()["videos"][0]["title"] == "Italian Game Explained"


def test_videos_route_503_when_not_configured() -> None:
    app = create_app()
    app.dependency_overrides[get_youtube_service] = lambda: YoutubeService(
        settings=Settings(youtube_api_key="")
    )
    client = TestClient(app)

    response = client.get("/api/v1/videos/Ouverture italienne")

    assert response.status_code == 503
