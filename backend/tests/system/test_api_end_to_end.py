"""The API started as a process, on a port, with none of its six services behind it.

Every other tier of this suite holds the application object and calls into it, which settles
routing and shapes and proves nothing about the command the README prints. An entry point
that stopped importing, a settings class that raises on a missing variable, a port that is
already held: none of the three reaches a test client, and all three reach the first
`docker compose up`.

The second thing this tier is for is the degradation. Six containers back this coach, and a
reader running the API alone has none of them: no Milvus, no Mongo, no Stockfish binary, no
Lichess token. What must still work is the part that needs nothing, and what must fail must
fail with a status code rather than a traceback. That is a property only a real process with
nothing behind it can show.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator

import pytest

from chess_coach.utils.paths import ROOT_DIR

pytestmark = pytest.mark.system

BOOT_TIMEOUT = 120
PREFIX = "/api/v1"

#: The starting position, which needs no service at all to describe.
START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

#: After 1.e4 e5 2.Nf3 Nc6 3.Bb5: the Ruy Lopez, the position the README shows.
RUY_LOPEZ = "r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3"


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _get(url: str, timeout: float = 30.0) -> tuple[int, dict]:
    try:
        # The address is always a loopback port this fixture opened itself.
        with urllib.request.urlopen(url, timeout=timeout) as answer:
            return answer.status, json.loads(answer.read().decode("utf-8"))
    except urllib.error.HTTPError as refusal:
        body = refusal.read().decode("utf-8")
        try:
            return refusal.code, json.loads(body)
        except json.JSONDecodeError:
            return refusal.code, {"raw": body}


@pytest.fixture(scope="module")
def service(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    """Start the API the way `backend/README.md` says to, with nothing behind it."""
    port = _free_port()
    log = tmp_path_factory.mktemp("service") / "uvicorn.log"
    environment = {
        **os.environ,
        "PYTHONIOENCODING": "utf-8",
        # Every external address points somewhere closed. That is the case under test.
        "MILVUS_HOST": "127.0.0.1",
        "MILVUS_PORT": "1",
        "MONGO_URI": "mongodb://127.0.0.1:1",
        "LICHESS_TOKEN": "",
        "YOUTUBE_API_KEY": "",
        "LLM_API_KEY": "",
    }
    # A file, because no thread here is reading the child's output, and an unread pipe
    # eventually stops the process that writes into it.
    with log.open("w", encoding="utf-8") as handle:
        # A fixed argv, no shell: the port is the only value that varies.
        server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "chess_coach.api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=str(ROOT_DIR),
            env=environment,
            stdout=handle,
            stderr=subprocess.STDOUT,
        )
        base = f"http://127.0.0.1:{port}{PREFIX}"
        try:
            deadline = time.monotonic() + BOOT_TIMEOUT
            while time.monotonic() < deadline:
                if server.poll() is not None:
                    pytest.fail(
                        f"uvicorn stopped with {server.returncode}:\n"
                        f"{log.read_text(encoding='utf-8', errors='replace')[-4000:]}"
                    )
                try:
                    status, _ = _get(f"{base}/healthcheck", timeout=2.0)
                except (urllib.error.URLError, OSError, TimeoutError):
                    time.sleep(0.5)
                    continue
                if status == 200:
                    break
            else:
                pytest.fail(
                    "the service never answered /healthcheck:\n"
                    f"{log.read_text(encoding='utf-8', errors='replace')[-4000:]}"
                )
            yield base
        finally:
            server.terminate()
            try:
                server.wait(timeout=20)
            except subprocess.TimeoutExpired:
                server.kill()


def test_the_command_in_the_readme_starts_something_that_answers(service: str) -> None:
    """`uvicorn chess_coach.api.main:app`, and a liveness probe that says which service."""
    status, body = _get(f"{service}/healthcheck")

    assert status == 200
    assert body["service"] == "chess_coach"
    assert body["version"]


def test_a_position_is_described_with_no_service_behind_it(service: str) -> None:
    """The board is arithmetic. It needs no engine, no database and no network."""
    status, body = _get(f"{service}/position/{urllib.parse.quote(START_FEN)}")

    assert status == 200
    assert body["side_to_move"] == "white"
    assert len(body["legal_moves_san"]) == 20
    assert body["board_ascii"].count("\n") == 7


def test_an_invalid_position_is_refused_with_a_status_and_not_a_traceback(service: str) -> None:
    """A FEN a caller mistyped is a 422 that names it, from a real process."""
    status, body = _get(f"{service}/position/not-a-fen")

    assert status == 422
    assert "not-a-fen" in json.dumps(body)


def test_the_documentation_page_is_served(service: str) -> None:
    """`/docs` is the page the README points a reader at, and it is generated."""
    with urllib.request.urlopen(
        service.replace(PREFIX, "") + "/openapi.json", timeout=30
    ) as answer:
        schema = json.loads(answer.read().decode("utf-8"))

    assert status_ok(schema)
    assert f"{PREFIX}/position/{{fen}}" in schema["paths"]
    assert f"{PREFIX}/coach" in schema["paths"] or f"{PREFIX}/agent" in schema["paths"]


def status_ok(schema: dict) -> bool:
    return bool(schema.get("openapi")) and bool(schema.get("paths"))


def test_a_route_that_needs_a_service_fails_as_a_status_code(service: str) -> None:
    """Milvus is not there. The search must answer with an error, and stay up.

    The point is the second half: after the failure, the process is still serving. A route
    that takes the whole application down with it when a dependency is missing is the
    failure this tier exists to catch.
    """
    status, _ = _get(f"{service}/vector-search?q=ruy%20lopez&top_k=2")

    assert status == 503, "a search with no vector store behind it answers 503, not 500"
    assert _get(f"{service}/healthcheck")[0] == 200, "and the service is still up"


def test_the_coach_describes_the_ruy_lopez_position_without_its_sources(service: str) -> None:
    """The position half of the answer holds even when every source is unreachable."""
    status, body = _get(f"{service}/position/{urllib.parse.quote(RUY_LOPEZ)}")

    assert status == 200
    assert body["side_to_move"] == "black"
    assert body["fen"].startswith("r1bqkbnr/pppp1ppp")
