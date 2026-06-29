"""Pydantic response models exposed by the API.

Keeping the response schemas in one place documents the public contract of the
service and lets FastAPI generate an accurate OpenAPI / Swagger description.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Returned by ``GET /api/v1/healthcheck``."""

    status: Literal["ok"] = "ok"
    service: str = Field(description="Name of the running service.")
    version: str = Field(description="Deployed package version.")
