"""The two published figures, redrawn into a temporary directory.

A figure script is the one piece of code whose output a diff cannot show: a PNG changes by a
pixel and the review passes over it. What can be checked is everything around the picture:
that both figures are drawn from the tracked artefacts and not from numbers typed into the
script, that the writer accepted them, and that the manifest it wrote carries the axis labels
and the sample size a reader needs to interpret them.

Nothing here looks at the image. `figure_style.save_figure` already refuses a figure with an
unlabelled axis or an unnamed spread, and these tests are what proves that refusal was not
triggered on the way past.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")

from scripts import build_figures


@pytest.fixture
def figures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect the figure directory, so a test never rewrites what is published."""
    monkeypatch.setattr(build_figures, "FIGURES_DIR", tmp_path)
    build_figures.apply_style()
    return tmp_path


def manifest_of(directory: Path) -> dict:
    return json.loads((directory / "MANIFEST.json").read_text(encoding="utf-8"))["images"]


def test_the_routing_figure_is_drawn_from_the_committed_sweep(figures: Path) -> None:
    build_figures.routing_plateau()

    entry = manifest_of(figures)["routing_plateau.png"]
    assert (figures / "routing_plateau.png").is_file()
    assert entry["n"] == "n = 54"
    assert entry["source"] == "scripts/build_figures.py"


def test_the_latency_figure_carries_the_count_of_each_node(figures: Path) -> None:
    """Four nodes, and the engine runs on half the sample: one figure, four sample sizes."""
    build_figures.latency_by_node()

    entry = manifest_of(figures)["latency_by_node.png"]
    assert "n(context) = 12" in entry["n"]
    assert "n(engine) = 6" in entry["n"]


def test_both_figures_label_their_axes(figures: Path) -> None:
    """An axis with no unit is a number nobody can read, and the writer refuses one."""
    build_figures.routing_plateau()
    build_figures.latency_by_node()

    for entry in manifest_of(figures).values():
        axes = entry["axes"][0]
        assert axes["x"] and axes["y"] and axes["title"]
        assert "millisecond" in axes["x"] or "master games" in axes["x"]


def test_neither_figure_claims_a_spread_it_did_not_draw(figures: Path) -> None:
    """One reading per position, and twelve timings: neither supports an interval."""
    build_figures.routing_plateau()
    build_figures.latency_by_node()

    assert all(entry["dispersion"] is None for entry in manifest_of(figures).values())


def test_the_served_threshold_is_the_one_the_settings_serve() -> None:
    """The dotted line on the first figure marks a value `config.py` decides, not the script."""
    from chess_coach.config import Settings

    assert Settings().theory_min_games == build_figures.SERVED_THRESHOLD
