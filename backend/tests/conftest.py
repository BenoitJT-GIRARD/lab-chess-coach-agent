"""What every tier of this suite shares: where the repository is, and how a test is skipped.

The suite is read by tier — ``unit/``, ``integration/``, ``system/`` — and each tier states
in its own ``conftest.py`` what it forbids. This file holds only what all three need.

**A skip names the command that would run the test.** A skip whose reason is a condition —
``"needs the database"``, ``"no model on disk"`` — teaches a reader that the test is
unrunnable. A skip that says ``run: docker compose up -d postgres`` teaches them how to run
it. Use :func:`skip_unless` and the message writes itself.
"""

from __future__ import annotations

import os
import socket
from pathlib import Path

import pytest

from chess_coach.utils.paths import ROOT_DIR as ROOT

# The root is NOT recomputed here: the import above takes it from the package, which already
# decides where the repository is. A second answer to that question is a second answer.


def skip_unless(condition: bool, *, command: str) -> pytest.MarkDecorator:
    """Skip the test unless the condition holds, naming the command that makes it hold.

    @skip_unless(port_is_open(5432), command="docker compose up -d postgres")
    def test_the_api_writes_its_prediction_to_the_database(): ...
    """
    return pytest.mark.skipif(not condition, reason=f"run: {command}")


def port_is_open(port: int, host: str = "127.0.0.1", timeout: float = 0.25) -> bool:
    """Is something listening? Asked once at collection, never retried in a loop."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def env_is_set(name: str) -> bool:
    """Is this environment variable set to something?

    A test gated on a variable that no workflow and no documented command ever sets skips on
    every checkout, and the count of tests it belongs to is a count of tests nobody runs.
    """
    return bool(os.environ.get(name))


@pytest.fixture(scope="session")
def root() -> Path:
    """The repository root, for a test that must open a published artefact."""
    return ROOT
