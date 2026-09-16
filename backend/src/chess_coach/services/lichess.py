"""Lichess Opening Explorer client.

The Opening Explorer answers, for a given position, with the moves that have
actually been played, their win/draw/loss statistics, the name of the opening,
and a handful of reference games. It is the agent's source of *theoretical*
moves and of the reference games shown beside them.

Two databases are available. ``lichess`` aggregates every rated game played on
the site — hundreds of millions, including a lot of beginner improvisation —
while ``masters`` only holds over-the-board master games. We query ``masters``:
those are the reference games, and their much smaller volume is what lets us
tell a studied line apart from a position nobody plays.

The endpoint requires an authenticated request; a personal Lichess token
(no scope needed) is read from ``LICHESS_TOKEN``. Requests are issued one at a
time with an explicit timeout, as the Lichess API guidelines ask.
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
class ReferenceGame:
    """One master game reaching the position, as shown by the Explorer."""

    game_id: str
    white: str
    black: str
    white_rating: int
    black_rating: int
    winner: str  # "white", "black" or "draw"
    year: int | None

    @property
    def url(self) -> str:
        """Link to the game on Lichess."""

        return f"https://lichess.org/{self.game_id}"

    @property
    def result(self) -> str:
        """The result written the way a chess database writes it."""

        if self.winner == "white":
            return "1-0"
        if self.winner == "black":
            return "0-1"
        return "1/2-1/2"


@dataclass(slots=True)
class OpeningExplorerResult:
    """Aggregated theory for a position."""

    fen: str
    opening_name: str | None
    opening_eco: str | None
    total_games: int
    moves: list[TheoryMove] = field(default_factory=list)
    # Whether the position belongs to known opening theory. It is a plain field
    # rather than a computed property because the rule that decides it depends
    # on the source: a curated opening book is theory by construction, while an
    # Explorer answer has to be judged on how many games back it.
    in_theory: bool = False
    reference_games: list[ReferenceGame] = field(default_factory=list)


class LichessService:
    """Thin wrapper around the Lichess Opening Explorer HTTP API."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._base_url = self._settings.lichess_explorer_base
        self._timeout = self._settings.http_timeout

    def _headers(self) -> dict[str, str]:
        """Build the request headers (meaningful User-Agent, bearer token)."""

        headers = {"User-Agent": "chess_coach-ffe-poc/0.1 (educational project)"}
        if self._settings.lichess_token:
            headers["Authorization"] = f"Bearer {self._settings.lichess_token}"
        return headers

    @property
    def is_configured(self) -> bool:
        """Whether a Lichess token is available (the Explorer requires one)."""

        return bool(self._settings.lichess_token)

    def get_theoretical_moves(
        self,
        fen: str,
        *,
        database: str | None = None,
        moves: int = 8,
    ) -> OpeningExplorerResult:
        """Return the theoretical moves played from ``fen``.

        Parameters
        ----------
        fen:
            The position to look up.
        database:
            ``"masters"`` (over-the-board master games, the default) or
            ``"lichess"`` (every rated game played on the site).
        moves:
            Maximum number of candidate moves to return.
        """

        database = database or self._settings.lichess_database
        url = f"{self._base_url}/{database}"
        params = {
            "fen": fen,
            "moves": moves,
            "topGames": self._settings.lichess_reference_games,
        }
        try:
            response = httpx.get(url, params=params, headers=self._headers(), timeout=self._timeout)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise LichessServiceError("Lichess request timed out") from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 429:
                raise LichessServiceError("Lichess rate limit reached (HTTP 429)") from exc
            if status == 401:
                raise LichessServiceError("Lichess refused the token (HTTP 401)") from exc
            raise LichessServiceError(f"Lichess returned HTTP {status}") from exc
        except httpx.HTTPError as exc:
            raise LichessServiceError("Lichess request failed") from exc

        return self._parse(fen, response.json(), self._settings.theory_min_games)

    @staticmethod
    def _parse(fen: str, payload: dict, min_games: int) -> OpeningExplorerResult:
        """Map the raw Explorer JSON onto :class:`OpeningExplorerResult`.

        ``min_games`` is the number of reference games below which a position
        is considered out of theory. Almost any legal position gets some answer
        back, and a line reached forty-eight times in the whole database is a
        curiosity: nothing a young player should be taught as theory.
        """

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
            in_theory=bool(moves) and total_games >= min_games,
            reference_games=[
                LichessService._parse_game(game) for game in payload.get("topGames", [])
            ],
        )

    @staticmethod
    def _parse_game(game: dict) -> ReferenceGame:
        """Map one entry of the Explorer's ``topGames`` list."""

        white = game.get("white") or {}
        black = game.get("black") or {}
        return ReferenceGame(
            game_id=game.get("id", ""),
            white=white.get("name", "?"),
            black=black.get("name", "?"),
            white_rating=white.get("rating", 0),
            black_rating=black.get("rating", 0),
            winner=game.get("winner") or "draw",
            year=game.get("year"),
        )
