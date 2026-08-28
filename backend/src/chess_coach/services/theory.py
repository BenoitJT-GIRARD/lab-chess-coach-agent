"""Theory service: a resilient source of theoretical moves.

It combines two sources so the agent always has an answer:

1. **Lichess Opening Explorer** — richer (real game statistics, authoritative
   opening names) but it now requires an authenticated token. Used first when a
   token is configured.
2. **Local opening book** — a small, offline book of main lines. Always
   available, so the POC runs without any external dependency.

If neither source knows the position, it is considered *out of theory* and the
caller (the agent) will turn to the Stockfish engine instead.
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

        # 1) Prefer Lichess when a token is configured and the call succeeds.
        if self._lichess.is_configured:
            try:
                remote = self._lichess.get_theoretical_moves(fen)
                if remote.in_theory:
                    return remote
            except LichessServiceError:
                # Network/rate-limit problems must not break the agent: fall back.
                pass

        # 2) Local opening book.
        book = OpeningBook.lookup(fen)
        if book is not None:
            return book

        # 3) Out of theory.
        return OpeningExplorerResult(
            fen=fen,
            opening_name=None,
            opening_eco=None,
            total_games=0,
            moves=[],
        )
