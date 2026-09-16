"""What `create_app` assembles, checked without starting anything.

Three facts below are read by something outside this repository and would break it quietly.
The prefix is what `frontend/proxy.conf.json` and `frontend/nginx.conf` route on; the allowed
origin is what the browser enforces; the version is what the healthcheck publishes. None of
them shows up in a unit test of a route, because a route knows nothing about where it is
mounted.
"""

from __future__ import annotations

import logging

import pytest

from chess_coach import __version__
from chess_coach.api import main
from chess_coach.api.main import API_PREFIX, create_app


def test_each_call_builds_its_own_application() -> None:
    """The suite builds an application per test; the module-level one is for uvicorn."""
    first, second = create_app(), create_app()

    assert first is not second


def test_every_published_route_is_mounted_under_the_versioned_prefix() -> None:
    """`frontend/nginx.conf` forwards `/api/` and nothing else, so a route outside is unreachable.

    The paths are read from the generated schema rather than from the router objects: the
    schema is what a client is written against, and it is the only listing that survives a
    change in how FastAPI represents an included router.
    """
    paths = set(create_app().openapi()["paths"])

    outside = sorted(path for path in paths if not path.startswith(API_PREFIX))
    assert outside == [], f"routes the frontend cannot reach: {outside}"


def test_the_eight_routers_are_all_mounted() -> None:
    """A router added to `main.py` and never included is a route that answers 404 in production."""
    paths = set(create_app().openapi()["paths"])

    assert len(paths) == 8, sorted(paths)


def test_the_browser_is_allowed_exactly_one_origin() -> None:
    """A wildcard here would be a decision nobody took, and it reads as a default."""
    origins = [
        middleware.kwargs.get("allow_origins")
        for middleware in create_app().user_middleware
        if "CORS" in middleware.cls.__name__
    ]

    assert origins == [["http://localhost:4200"]]


def test_the_published_schema_carries_the_package_version() -> None:
    """The version in `/openapi.json` and the one in `/healthcheck` have one source."""
    schema = create_app().openapi()

    assert schema["info"]["version"] == __version__


def test_a_warm_up_that_cannot_load_its_model_does_not_stop_the_service(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """No network, no cache, no model. The coach still answers everything that is arithmetic.

    The warm-up exists so the first question does not pay for the model load. It must not
    become a second way for the service to fail to start.
    """
    import chess_coach.services.embeddings as embeddings

    def refuse(self: object, *args: object, **kwargs: object) -> None:
        raise OSError("we have no colours here")

    monkeypatch.setattr(embeddings.EmbeddingService, "embed_one", refuse)

    with caplog.at_level(logging.WARNING):
        main.warm_embeddings()

    assert "not warmed up" in caplog.text
