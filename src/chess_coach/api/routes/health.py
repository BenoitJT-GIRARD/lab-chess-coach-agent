"""Health-check route.

A trivial endpoint used to verify that the container is up and that the API
process answers requests. It is the very first thing the Docker healthcheck and
the Angular frontend probe.
"""

from __future__ import annotations

from fastapi import APIRouter

from chess_coach import __version__
from chess_coach.api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/healthcheck", response_model=HealthResponse, summary="Liveness probe")
def healthcheck() -> HealthResponse:
    """Return a static payload proving the service is alive."""

    return HealthResponse(service="chess_coach", version=__version__)
