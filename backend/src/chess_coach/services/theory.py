"""Theory service: a resilient source of theoretical moves.

It combines two sources so the agent always has an answer:

1. **Lichess Opening Explorer** — the reference source. It returns the moves
   played in master games, their statistics, the name of the opening and a few
   reference games. It needs an authenticated token.
2. **Local opening book** — a small, offline book of main lines. It takes over
   when no token is configured or when the call fails, so the POC keeps
   working without any external dependency.

If neither source knows the position, it is considered *out of theory* and the
caller (the agent) turns to the Stockfish engine instead.
"""

from __future__ import annotations

from chess_coach.config import Settings, get_settings
from chess_coach.services.lichess import LichessService, LichessServiceError, OpeningExplorerResult
from chess_coach.services.opening_book import OpeningBook


class TheoryService:
    """Return theoretical moves from Lichess when possible, else the local book."""

    def __init__(
        self,
        settings: Settings | None = None,
        lichess: LichessService | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._lichess = lichess or LichessService(self._settings)

    def get_theoretical_moves(self, fen: str) -> OpeningExplorerResult:
        """Return the best available theory for ``fen``."""

        # 1) Lichess first, whenever a token is configured.
        if self._lichess.is_configured:
            try:
                remote = self._lichess.get_theoretical_moves(fen)
                if remote.in_theory:
                    return remote
                # Lichess answered but the position is not established theory.
                # The local book may still know it (a main line the master
                # database happens to be thin on), so we keep looking.
            except LichessServiceError:
                # Network or rate-limit problems must not break the agent.
                pass

        # 2) Local opening book.
        book = OpeningBook.lookup(fen)
        if book is not None:
            return book

        # 3) Out of theory: the agent will call the engine.
        return OpeningExplorerResult(
            fen=fen,
            opening_name=None,
            opening_eco=None,
            total_games=0,
            moves=[],
            in_theory=False,
        )
