"""Lichess Opening Explorer client.

The Opening Explorer aggregates millions of games and, for a given position,
returns the moves that have actually been played together with their win/draw/
loss statistics and the name of the opening. It is the agent's source of
*theoretical* moves.

The public Explorer endpoint (``https://explorer.lichess.ovh``) needs no
authentication. We only ever issue one request at a time and always pass an
explicit timeout, as recommended by the Lichess API guidelines.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx

from chess_coach.config import Settings, get_settings


class LichessServiceError(RuntimeError):
    """Raised when the Lichess Opening Explorer cannot be queried."""


@dataclass(slots=True)
class TheoryMove:
    """A single candidate move with its aggregated game statistics."""

    uci: str
    san: str
    white: int
    draws: int
    black: int
    source: str = "lichess"  # "lichess" (game stats) or "book" (local theory)

    @property
    def total(self) -> int:
        """Total number of games in which this move was played."""

        return self.white + self.draws + self.black


@dataclass(slots=True)
class OpeningExplorerResult:
    """Aggregated theory for a position."""

    fen: str
    opening_name: str | None
    opening_eco: str | None
    total_games: int
    moves: list[TheoryMove] = field(default_factory=list)

    @property
    def in_theory(self) -> bool:
        """Whether the position is known to opening theory (has played moves)."""

        return bool(self.moves)


class LichessService:
    """Thin wrapper around the Lichess Opening Explorer HTTP API."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._base_url = self._settings.lichess_explorer_base
        self._timeout = self._settings.http_timeout

    def _headers(self) -> dict[str, str]:
        """Build the request headers (meaningful User-Agent, optional token)."""

        headers = {"User-Agent": "chess_coach-ffe-poc/0.1 (educational project)"}
        if self._settings.lichess_token:
            headers["Authorization"] = f"Bearer {self._settings.lichess_token}"
        return headers

    @property
    def is_configured(self) -> bool:
        """Whether a Lichess token is available (the Explorer now requires one)."""

        return bool(self._settings.lichess_token)

    def get_theoretical_moves(
        self,
        fen: str,
        *,
        database: str = "lichess",
        moves: int = 8,
    ) -> OpeningExplorerResult:
        """Return the theoretical moves played from ``fen``.

        Parameters
        ----------
        fen:
            The position to look up.
        database:
            ``"lichess"`` (all rated games) or ``"masters"`` (over-the-board
            master games, i.e. reference games).
        moves:
            Maximum number of candidate moves to return.
        """

        url = f"{self._base_url}/{database}"
        params = {"fen": fen, "moves": moves}
        try:
            response = httpx.get(url, params=params, headers=self._headers(), timeout=self._timeout)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise LichessServiceError("Lichess request timed out") from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 429:
                raise LichessServiceError("Lichess rate limit reached (HTTP 429)") from exc
            raise LichessServiceError(f"Lichess returned HTTP {status}") from exc
        except httpx.HTTPError as exc:
            raise LichessServiceError("Lichess request failed") from exc

        return self._parse(fen, response.json())

    @staticmethod
    def _parse(fen: str, payload: dict) -> OpeningExplorerResult:
        """Map the raw Explorer JSON onto :class:`OpeningExplorerResult`."""

        opening = payload.get("opening") or {}
        moves = [
            TheoryMove(
                uci=move.get("uci", ""),
                san=move.get("san", ""),
                white=move.get("white", 0),
                draws=move.get("draws", 0),
                black=move.get("black", 0),
            )
            for move in payload.get("moves", [])
        ]
        total_games = payload.get("white", 0) + payload.get("draws", 0) + payload.get("black", 0)
        return OpeningExplorerResult(
            fen=fen,
            opening_name=opening.get("name"),
            opening_eco=opening.get("eco"),
            total_games=total_games,
            moves=moves,
        )
