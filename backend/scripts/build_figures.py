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
import numpy as np

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
    """Each measurement where the run recorded them, and the order statistics otherwise.

    Two bars per node — the median beside the ninetieth percentile — asked the eye to compare
    two lengths that are not independent: the p90 of a sample contains its median, and a bar
    chart says the opposite. A latency is also not symmetric around its middle, so a mean and
    an interval would describe a shape it does not have. What is drawn is the median, the
    stretch from it to the p90, and the thin tail out to the slowest call.
    """
    payload = json.loads(LATENCY_JSON.read_text(encoding="utf-8"))
    nodes = payload["nodes"]
    order = sorted(nodes, key=lambda name: nodes[name]["median_ms"])
    positions = range(len(order))

    fig, ax = plt.subplots()
    scatterer = np.random.default_rng(20260916)
    for position, name in zip(positions, order, strict=True):
        node = nodes[name]
        samples = [float(value) for value in node.get("samples_ms") or []]
        if samples:
            ax.scatter(
                samples,
                position + scatterer.uniform(-0.16, 0.16, size=len(samples)),
                s=16,
                color=PALETTE["tertiary"],
                alpha=0.55,
                linewidths=0,
                zorder=2,
            )
        ax.hlines(
            position,
            node["median_ms"],
            node["max_ms"],
            color=PALETTE["control"],
            linewidth=1.0,
            zorder=3,
        )
        ax.hlines(
            position,
            node["median_ms"],
            node["p90_ms"],
            color=PALETTE["primary"],
            linewidth=3.4,
            zorder=4,
        )
        ax.scatter(
            [node["median_ms"]],
            [position],
            s=44,
            color=PALETTE["primary"],
            zorder=5,
            label="median" if position == 0 else None,
        )
    ax.plot([], [], color=PALETTE["primary"], linewidth=3.4, label="median to p90")
    ax.plot([], [], color=PALETTE["control"], linewidth=1.0, label="p90 to slowest call")
    # Logarithmic, because the four nodes span 18 ms to 8 seconds: on a linear axis the one
    # cold start of the context node flattens the other three into the same pixel column.
    ax.set_xscale("log")
    ax.set_yticks(list(positions))
    ax.set_yticklabels(order)
    ax.set_xlabel("Wall-clock time of one node, in milliseconds (log scale)")
    ax.set_ylabel("Node of the agent's graph")
    ax.set_title("Wall-clock cost of each node of the agent's graph")
    ax.legend(loc="upper right", fontsize=8, frameon=False)

    counts = {name: nodes[name]["n"] for name in order}
    _breathe(fig)
    save_figure(
        fig,
        FIGURES_DIR / "latency_by_node.png",
        n=counts,
        source=SOURCE,
        note="4 positions, 3 repeats, language model disabled; order statistics of a skewed "
        "sample, so no mean and no interval is drawn",
    )
    close(fig)


def main() -> None:
    apply_style()
    routing_plateau()
    latency_by_node()
    print(f"2 figures written under {FIGURES_DIR}")


if __name__ == "__main__":
    main()
