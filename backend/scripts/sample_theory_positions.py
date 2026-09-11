"""Ask the Opening Explorer how many master games back a set of positions, once.

The Explorer is a living database: the count for a position changes from one month to the
next. A sweep that queried it live would not be replayable, so the reading is taken once
and frozen, with its date, in ``data/eval/theory_positions.json``. Everything downstream
reads that file and touches no network.

The positions are walked from the curated opening book — main lines at several depths —
plus a handful of lines nobody plays, which is where a routing threshold earns its keep.

    LICHESS_TOKEN=... uv run python -m scripts.sample_theory_positions
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

import chess

from chess_coach.config import get_settings
from chess_coach.services.lichess import LichessService, LichessServiceError
from chess_coach.services.opening_book import OPENING_LINES

OUT = Path("data/eval/theory_positions.json")

#: The Explorer is free and rate-limited. One request per second is the pace it tolerates;
#: without this pause the run dies on HTTP 429 after about twenty positions, and the ones
#: it loses are the tail of the list rather than a random sample.
PAUSE_SECONDS = 1.5
RETRIES = 3

#: Lines that carry a name but almost no master games. They are the reason a threshold
#: exists: the Explorer answers for them, and answering is not the same as being theory.
CURIOSITIES: list[tuple[str, list[str]]] = [
    ("Scholar's Attack", ["e4", "e5", "Qh5"]),
    ("Bongcloud", ["e4", "e5", "Ke2"]),
    ("Grob", ["g4"]),
    ("Barnes Opening", ["f3"]),
    ("Desprez Opening", ["h4"]),
    ("Anderssen Opening", ["a3"]),
    ("Sodium Attack", ["Na3"]),
    ("Ware Opening", ["a4"]),
]

#: Depths at which each curated line is sampled. A main line is theory at move 2 and much
#: thinner at move 10, and the sweep needs both ends.
DEPTHS = (2, 4, 6, 8, 10)


def positions_to_sample() -> list[dict]:
    """Walk the book's lines and the curiosities into (name, ply, FEN) triples."""

    seen: set[str] = set()
    sampled: list[dict] = []

    def add(name: str, moves: list[str]) -> None:
        board = chess.Board()
        for san in moves:
            try:
                board.push_san(san)
            except ValueError:
                return
        fen = board.fen()
        if fen in seen:
            return
        seen.add(fen)
        sampled.append({"name": name, "ply": len(moves), "fen": fen})

    for name, _eco, moves in OPENING_LINES:
        for depth in DEPTHS:
            if depth <= len(moves):
                add(name, moves[:depth])
    for name, moves in CURIOSITIES:
        add(name, moves)
    return sampled


def main() -> None:
    settings = get_settings()
    service = LichessService(settings)
    if not service.is_configured:
        raise SystemExit(
            "LICHESS_TOKEN is not set. The Opening Explorer refuses anonymous requests, "
            "and this is the only script here that needs it."
        )

    rows = []
    for entry in positions_to_sample():
        result = None
        for attempt in range(RETRIES):
            try:
                result = service.get_theoretical_moves(entry["fen"])
                break
            except LichessServiceError as exc:
                wait = PAUSE_SECONDS * (attempt + 2)
                print(f"  {entry['name']:28s} ply {entry['ply']:2d}  {exc} — retry in {wait:.0f}s")
                time.sleep(wait)
        if result is None:
            print(f"  {entry['name']:28s} ply {entry['ply']:2d}  given up")
            continue
        time.sleep(PAUSE_SECONDS)
        rows.append(
            {
                **entry,
                "explorer_name": result.opening_name,
                "eco": result.opening_eco,
                "total_games": result.total_games,
                "n_moves": len(result.moves),
            }
        )
        print(f"  {entry['name']:28s} ply {entry['ply']:2d}  {result.total_games:>9d} parties")

    payload = {
        "read_on": datetime.now(UTC).date().isoformat(),
        "database": settings.lichess_database,
        "served_threshold": settings.theory_min_games,
        "note": (
            "Frozen reading of the Lichess Opening Explorer. The database is alive; these "
            "counts are what it answered on the date above, and the sweep runs on them so "
            "that it replays."
        ),
        "positions": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n{len(rows)} positions written to {OUT}")


if __name__ == "__main__":
    main()
