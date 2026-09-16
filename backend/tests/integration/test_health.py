"""Tests for the health-check endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from chess_coach import __version__
from chess_coach.api.main import create_app

pytestmark = pytest.mark.integration

client = TestClient(create_app())


def test_healthcheck_returns_ok() -> None:
    """The liveness probe answers 200 with the expected payload."""

    response = client.get("/api/v1/healthcheck")

    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "ok", "service": "chess_coach", "version": __version__}
