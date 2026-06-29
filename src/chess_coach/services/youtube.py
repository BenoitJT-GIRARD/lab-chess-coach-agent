"""YouTube Data API v3 client.

For a given opening, the agent proposes a few explanatory videos. We build a
focused search query (opening name + chess-learning keywords), keep only the
useful metadata, and degrade gracefully when no key is configured, the quota is
exhausted, or nothing relevant is found.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from chess_coach.config import Settings, get_settings


class YoutubeServiceError(RuntimeError):
    """Raised when the YouTube Data API cannot be queried."""


@dataclass(slots=True)
class VideoItem:
    """A single YouTube video result."""

    video_id: str
    title: str
    channel: str
    url: str
    thumbnail: str


class YoutubeService:
    """Search explanatory chess videos through the YouTube Data API."""

    def __init__(self, settings: Settings | None = None, client: Any | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = client

    @property
    def is_configured(self) -> bool:
        """Whether a YouTube API key is available."""

        return bool(self._settings.youtube_api_key)

    def _get_client(self) -> Any:
        """Build the YouTube API client lazily."""

        if self._client is None:
            if not self.is_configured:
                raise YoutubeServiceError("YOUTUBE_API_KEY is not configured")
            try:
                from googleapiclient.discovery import build

                self._client = build(
                    "youtube",
                    "v3",
                    developerKey=self._settings.youtube_api_key,
                    cache_discovery=False,
                )
            except Exception as exc:  # pragma: no cover - network/credentials
                raise YoutubeServiceError("Could not initialise the YouTube client") from exc
        return self._client

    @staticmethod
    def _build_query(opening: str) -> str:
        """Turn an opening name into a focused search query."""

        return f"{opening} chess opening tutorial explanation"

    def search_videos(self, opening: str, *, max_results: int = 5) -> list[VideoItem]:
        """Return up to ``max_results`` relevant videos for ``opening``."""

        client = self._get_client()
        try:
            response = (
                client.search()
                .list(
                    q=self._build_query(opening),
                    part="snippet",
                    type="video",
                    maxResults=max_results,
                    order="relevance",
                    safeSearch="strict",
                    videoEmbeddable="true",
                )
                .execute()
            )
        except Exception as exc:  # pragma: no cover - network/quota
            raise YoutubeServiceError("YouTube search failed (network or quota)") from exc

        return self._parse(response)

    @staticmethod
    def _parse(response: dict) -> list[VideoItem]:
        """Map the raw API response onto :class:`VideoItem` objects."""

        videos: list[VideoItem] = []
        for item in response.get("items", []):
            video_id = item.get("id", {}).get("videoId")
            if not video_id:
                continue
            snippet = item.get("snippet", {})
            thumbnails = snippet.get("thumbnails", {})
            thumb = (thumbnails.get("medium") or thumbnails.get("default") or {}).get("url", "")
            videos.append(
                VideoItem(
                    video_id=video_id,
                    title=snippet.get("title", ""),
                    channel=snippet.get("channelTitle", ""),
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    thumbnail=thumb,
                )
            )
        return videos
