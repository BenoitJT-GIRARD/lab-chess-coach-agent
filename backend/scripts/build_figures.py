"""Draw the two figures the README publishes, from the artefacts under `reports/`.

Both read a tracked file. The picture beside a table is therefore the same measurement the
table is, and one command redraws both:

    uv run python scripts/build_figures.py

`chess_coach.figure_style` gives the colours, and it is also what writes the file. It turns
down a figure whose axes are unlabelled, and one that draws a spread without saying what the
spread covers. Neither figure here draws a spread. A sweep over a reading taken once has no
sampling error to show, and twelve timings carry an order statistic and not an interval; each
caption says as much, because a reader is otherwise entitled to wonder what was left out.
"""

from __future__ import annotations

import csv
import json

import matplotlib.pyplot as plt

from chess_coach.figure_style import PALETTE, apply_style, close, save_figure
from chess_coach.utils.paths import FIGURES_DIR, LATENCY_JSON, THRESHOLD_SWEEP_CSV

SOURCE = "scripts/build_figures.py"

#: The value `config.py` serves, and the one the sweep is read around.
SERVED_THRESHOLD = 1000


def _breathe(fig: plt.Figure) -> None:
    """Leave the stamp its line.

    The sample size is stamped below everything else, and the tight bounding box crops to
    what has been drawn. The two together put that line through the x-axis label unless the
    bottom margin is widened first.
    """
    fig.tight_layout()
    fig.subplots_adjust(bottom=fig.subplotpars.bottom + 0.08)


def routing_plateau() -> None:
    """How many positions the routing sends to theory, across the threshold."""
    with THRESHOLD_SWEEP_CSV.open(encoding="utf-8", newline="") as handle:
        rows = [{key: int(value) for key, value in row.items()} for row in csv.DictReader(handle)]

    thresholds = [row["threshold"] for row in rows]
    in_theory = [row["in_theory"] for row in rows]
    total = rows[0]["in_theory"] + rows[0]["out_of_theory"]

    fig, ax = plt.subplots()
    ax.plot(thresholds, in_theory, marker="o", color=PALETTE["primary"])
    ax.axvline(SERVED_THRESHOLD, color=PALETTE["secondary"], linestyle=":", linewidth=1.6)
    ax.annotate(
        f"served: {SERVED_THRESHOLD}",
        xy=(SERVED_THRESHOLD, max(in_theory)),
        xytext=(6, -4),
        textcoords="offset points",
        color=PALETTE["secondary"],
        fontsize=9,
    )
    # Symlog rather than log: the sweep starts at zero, which a log axis cannot place. The
    # left limit is set explicitly, because symlog otherwise draws the negative decades of a
    # quantity that has none.
    ax.set_xscale("symlog", linthresh=10)
    ax.set_xlim(left=-1, right=max(thresholds) * 1.4)
    ax.set_xlabel("Threshold, in master games reaching the position")
    ax.set_ylabel("Positions the agent answers from theory")
    # The title says what is plotted; reading it is the README's job.
    ax.set_title("Positions routed to theory, across the threshold, on the frozen reading")
    ax.set_ylim(0, total + 2)

    _breathe(fig)
    save_figure(
        fig,
        FIGURES_DIR / "routing_plateau.png",
        n=total,
        source=SOURCE,
        note="frozen Explorer reading, 2026-09-07; no spread to draw, one reading per position",
    )
    close(fig)


def latency_by_node() -> None:
    """What each node of the graph costs, median and ninetieth percentile."""
    payload = json.loads(LATENCY_JSON.read_text(encoding="utf-8"))
    nodes = payload["nodes"]
    order = sorted(nodes, key=lambda name: nodes[name]["median_ms"])

    medians = [nodes[name]["median_ms"] for name in order]
    p90s = [nodes[name]["p90_ms"] for name in order]
    positions = range(len(order))

    fig, ax = plt.subplots()
    ax.barh(
        [position + 0.18 for position in positions],
        medians,
        height=0.34,
        color=PALETTE["primary"],
        label="median",
    )
    ax.barh(
        [position - 0.18 for position in positions],
        p90s,
        height=0.34,
        color=PALETTE["tertiary"],
        label="p90",
    )
    ax.set_yticks(list(positions))
    ax.set_yticklabels(order)
    ax.set_xlabel("Wall-clock time of one node, in milliseconds")
    ax.set_ylabel("Node of the agent's graph")
    ax.set_title("Wall-clock cost of each node of the graph, median and ninetieth percentile")
    ax.legend(loc="lower right")

    counts = {name: nodes[name]["n"] for name in order}
    _breathe(fig)
    save_figure(
        fig,
        FIGURES_DIR / "latency_by_node.png",
        n=counts,
        source=SOURCE,
        note="4 positions, 3 repeats, language model disabled; p90 over 12 points is an "
        "order statistic, so no interval is drawn",
    )
    close(fig)


def main() -> None:
    apply_style()
    routing_plateau()
    latency_by_node()
    print(f"2 figures written under {FIGURES_DIR}")


if __name__ == "__main__":
    main()
