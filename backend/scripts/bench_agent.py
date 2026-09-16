"""What a request costs, node by node.

A stack of six containers should say what one question costs and which of the four
external calls dominates. It is the first number a reader looks for, and the repository
had none.

The language model is left **off**: the agent then falls back on its deterministic
template. Timing a billed call would make the bench cost money, and the variance of a
third-party endpoint would swamp the four nodes this is meant to compare.

    docker compose up -d
    LLM_ENABLED=false uv run python -m scripts.bench_agent
"""

from __future__ import annotations

import statistics
import time
from datetime import UTC, datetime

import chess

from chess_coach.agent.state import AgentDeps
from chess_coach.artifacts import write_json
from chess_coach.config import get_settings
from chess_coach.services.mongo import MongoService
from chess_coach.services.rag_search import RagService
from chess_coach.services.stockfish_engine import StockfishService
from chess_coach.services.theory import TheoryService
from chess_coach.services.youtube import YoutubeService
from chess_coach.utils.paths import LATENCY_JSON

OUT = LATENCY_JSON

#: Two positions in theory, two out of it — the graph takes a different path for each, and
#: an average over one of them would describe half the system.
LINES: list[tuple[str, list[str]]] = [
    ("Italian Game", ["e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5"]),
    ("Sicilian Defense", ["e4", "c5"]),
    ("Scholar's Attack (out of theory)", ["e4", "e5", "Qh5"]),
    ("Bongcloud (out of theory)", ["e4", "e5", "Ke2"]),
]
REPEATS = 3


def fen_of(moves: list[str]) -> str:
    board = chess.Board()
    for san in moves:
        board.push_san(san)
    return board.fen()


def measure_one(deps: AgentDeps, timed, name: str, fen: str) -> None:
    """Walk one position through the nodes the graph would take for it.

    Its own function so the closures handed to ``timed`` bind this position's ``fen``
    rather than whatever the enclosing loop last assigned.
    """

    theory = timed("theory", lambda: deps.theory.get_theoretical_moves(fen))
    if not theory.in_theory:
        timed("engine", lambda: deps.stockfish.evaluate(fen))
    opening = theory.opening_name or "chess opening"
    query = f"ouverture {opening}, idées et plans"
    timed("context", lambda: deps.rag.search(query, top_k=3))
    if deps.youtube.is_configured:
        timed("videos", lambda: deps.youtube.search_videos(opening, max_results=4))
    print(f"  {name:36s} {'theory' if theory.in_theory else 'engine'}")


def main() -> None:
    settings = get_settings()
    deps = AgentDeps(
        settings=settings,
        theory=TheoryService(settings),
        stockfish=StockfishService(settings),
        rag=RagService(settings),
        youtube=YoutubeService(settings),
        mongo=MongoService(settings),
    )

    # The nodes are timed through the services rather than through the compiled graph:
    # LangGraph reports a total, and the question here is which call dominates it.
    samples: dict[str, list[float]] = {}

    def timed(node: str, call) -> object:
        start = time.perf_counter()
        try:
            return call()
        finally:
            samples.setdefault(node, []).append((time.perf_counter() - start) * 1000)

    for _ in range(REPEATS):
        for name, moves in LINES:
            measure_one(deps, timed, name, fen_of(moves))

    payload = {
        "measured": datetime.now(UTC).date().isoformat(),
        "note": (
            "Language model disabled: the agent answers from its deterministic template. "
            "Timing a billed call would make the bench cost money and its variance would "
            "swamp the local nodes."
        ),
        "positions": [name for name, _ in LINES],
        "repeats": REPEATS,
        "nodes": {
            node: {
                "n": len(values),
                # Every measurement, not only the summary of them: a figure that shows
                # twelve points says whether a median of 18 ms came from twelve values at
                # 18 or from six at 5 and six at 40.
                "samples_ms": [round(value, 2) for value in sorted(values)],
                "median_ms": round(statistics.median(values), 1),
                "p90_ms": round(sorted(values)[max(0, int(len(values) * 0.9) - 1)], 1),
                "max_ms": round(max(values), 1),
            }
            for node, values in sorted(samples.items())
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    write_json(OUT, payload)

    print()
    for node, stats in payload["nodes"].items():
        print(
            f"  {node:10s} médiane {stats['median_ms']:>8.1f} ms   p90 {stats['p90_ms']:>8.1f} ms"
        )
    print(f"\nwritten: {OUT}")


if __name__ == "__main__":
    main()
