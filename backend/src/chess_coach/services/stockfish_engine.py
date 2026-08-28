"""Stockfish evaluation service.

When a position leaves known theory, the agent falls back on a specialised
engine to judge it. Stockfish returns both a numeric evaluation (in centipawns,
or a forced-mate distance) and the move it considers best.

The engine binary only exists inside the backend Docker image
(``/usr/games/stockfish``); the engine instance is therefore created lazily and
can be injected, which keeps the service unit-testable without the binary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from chess_coach.config import Settings, get_settings
from chess_coach.services.chess_position import uci_to_san


class StockfishServiceError(RuntimeError):
    """Raised when the Stockfish engine cannot evaluate a position."""


@dataclass(slots=True)
class EvaluationResult:
    """A Stockfish evaluation, always expressed from White's point of view."""

    fen: str
    evaluation_type: str  # "cp" (centipawns) or "mate"
    value: int
    best_move: str | None
    best_move_san: str | None
    depth: int


class StockfishService:
    """Wrapper around the ``stockfish`` Python binding."""

    def __init__(self, settings: Settings | None = None, engine: Any | None = None) -> None:
        self._settings = settings or get_settings()
        self._engine = engine

    def _get_engine(self) -> Any:
        """Lazily instantiate the Stockfish engine (cached for reuse)."""

        if self._engine is None:
            try:
                from stockfish import Stockfish

                self._engine = Stockfish(
                    path=self._settings.stockfish_path,
                    depth=self._settings.stockfish_depth,
                    parameters={"Threads": self._settings.stockfish_threads},
                )
            except Exception as exc:  # pragma: no cover - depends on the binary
                raise StockfishServiceError(
                    f"Could not start Stockfish at {self._settings.stockfish_path!r}"
                ) from exc
        return self._engine

    def evaluate(self, fen: str) -> EvaluationResult:
        """Evaluate ``fen`` and return the score and best move."""

        engine = self._get_engine()
        try:
            if not engine.is_fen_valid(fen):
                raise StockfishServiceError(f"Stockfish rejected the FEN: {fen!r}")
            engine.set_fen_position(fen)
            raw = engine.get_evaluation()
            best_move = engine.get_best_move()
        except StockfishServiceError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            raise StockfishServiceError("Stockfish evaluation failed") from exc

        best_move_san = uci_to_san(fen, best_move) if best_move else None
        return EvaluationResult(
            fen=fen,
            evaluation_type=raw.get("type", "cp"),
            value=raw.get("value", 0),
            best_move=best_move,
            best_move_san=best_move_san,
            depth=self._settings.stockfish_depth,
        )
