"""Read the frozen Explorer reading and write the routing curve.

Touches no network: everything comes from ``data/eval/theory_positions.json``, which
``sample_theory_positions.py`` wrote once with its date.

    uv run python -m scripts.sweep_theory_threshold
"""

from __future__ import annotations

import json

from chess_coach.artifacts import write_csv, write_text
from chess_coach.config import get_settings
from chess_coach.evaluation.threshold import plateau_around, sweep
from chess_coach.utils.paths import THEORY_POSITIONS, THRESHOLD_SWEEP_CSV, THRESHOLD_SWEEP_TABLE

READING = THEORY_POSITIONS
OUT_CSV = THRESHOLD_SWEEP_CSV
OUT_TABLE = THRESHOLD_SWEEP_TABLE

THRESHOLDS = [0, 10, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 25000, 50000]


def main() -> None:
    if not READING.exists():
        raise SystemExit(
            f"{READING} is missing. Run scripts/sample_theory_positions.py first — it is "
            "the only step that needs a Lichess token."
        )
    payload = json.loads(READING.read_text(encoding="utf-8"))
    positions = payload["positions"]
    served = get_settings().theory_min_games

    rows = sweep(positions, THRESHOLDS)
    room = plateau_around(positions, served)

    write_csv(OUT_CSV, ["threshold", "in_theory", "out_of_theory", "flipped"], rows)

    write_text(OUT_TABLE, render(payload, rows, room, served))
    for row in rows:
        mark = "  <- servi" if row["threshold"] == served else ""
        print(
            f"  seuil {row['threshold']:>6d} : {row['in_theory']:>3d} en théorie, "
            f"{row['flipped']:>2d} bascules{mark}"
        )
    print(f"\nwritten: {OUT_CSV} and {OUT_TABLE}")


def render(payload: dict, rows: list[dict], room: dict, served: int) -> str:
    n = len(payload["positions"])
    lines = [
        "# Routing threshold — how sharply the agent's only branch depends on it",
        "",
        f"- Explorer read on: {payload['read_on']} (database `{payload['database']}`)",
        f"- Positions: {n}, walked from the curated opening book at several depths, plus "
        "eight lines nobody plays",
        f"- Served threshold: **{served}** master games",
        "",
        "| Threshold | In theory | Out of theory | Positions that flipped |",
        "|---|---|---|---|",
    ]
    for row in rows:
        label = f"**{row['threshold']}**" if row["threshold"] == served else str(row["threshold"])
        lines.append(
            f"| {label} | {row['in_theory']} | {row['out_of_theory']} | {row['flipped']} |"
        )
    lines += [
        "",
        f"Divide the served threshold by {room['factor']:.0f} and "
        f"**{room['flipped_if_divided']} of {room['n']}** positions change side; multiply "
        f"it by {room['factor']:.0f} and **{room['flipped_if_multiplied']}** do.",
        "",
        "The reading is frozen on purpose. The Explorer is a living database and these "
        "counts move; the sweep runs on the file so that it replays.",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
