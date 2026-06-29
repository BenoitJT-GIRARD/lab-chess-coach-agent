"""Explanatory videos route (YouTube Data API v3)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from chess_coach.api.dependencies import get_youtube_service
from chess_coach.api.schemas import VideoResult, VideosResponse
from chess_coach.services.youtube import YoutubeService, YoutubeServiceError

router = APIRouter(tags=["videos"])


@router.get("/videos/{opening}", response_model=VideosResponse, summary="Explanatory videos")
def get_videos(
    opening: str,
    youtube: Annotated[YoutubeService, Depends(get_youtube_service)],
) -> VideosResponse:
    """Return explanatory YouTube videos for ``opening``."""

    if not youtube.is_configured:
        raise HTTPException(
            status_code=503,
            detail="YouTube is not configured (set YOUTUBE_API_KEY).",
        )

    try:
        videos = youtube.search_videos(opening)
    except YoutubeServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return VideosResponse(
        opening=opening,
        videos=[
            VideoResult(
                video_id=video.video_id,
                title=video.title,
                channel=video.channel,
                url=video.url,
                thumbnail=video.thumbnail,
            )
            for video in videos
        ],
    )
