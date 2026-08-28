"""Local opening book.

The Lichess Opening Explorer requires an authenticated token, and any network
call can fail. To keep the POC runnable in every case, the theoretical moves
are also served from a small, self-contained opening book built from the main
lines of the most popular openings.

The book is generated once at import time: each curated line is replayed with
python-chess and, for every position encountered, we record the move that
continues the line (in UCI and SAN) together with the name of the opening. The
position is keyed by its EPD (piece placement + side to move + castling rights +
en-passant square), which makes the lookup transposition-friendly and
independent of move counters.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import chess

from chess_coach.services.chess_position import parse_board
from chess_coach.services.lichess import OpeningExplorerResult, TheoryMove

# Curated main lines: (opening name, ECO code, moves in SAN).
# The first short "family" lines guarantee a sensible name for the very first
# move of the game; the detailed lines add the deeper, more specific theory.
OPENING_LINES: list[tuple[str, str, list[str]]] = [
    ("King's Pawn Opening", "B00", ["e4"]),
    ("Queen's Pawn Opening", "A40", ["d4"]),
    ("English Opening", "A10", ["c4"]),
    ("Réti Opening", "A04", ["Nf3"]),
    ("Italian Game", "C50", ["e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5", "c3", "Nf6", "d3", "d6"]),
    ("Ruy Lopez", "C60", ["e4", "e5", "Nf3", "Nc6", "Bb5", "a6", "Ba4", "Nf6", "O-O", "Be7"]),
    ("Scotch Game", "C45", ["e4", "e5", "Nf3", "Nc6", "d4", "exd4", "Nxd4", "Nf6"]),
    ("Petrov Defense", "C42", ["e4", "e5", "Nf3", "Nf6", "Nxe5", "d6", "Nf3", "Nxe4"]),
    (
        "Sicilian Defense, Najdorf",
        "B90",
        ["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "a6"],
    ),
    ("Sicilian Defense", "B40", ["e4", "c5", "Nf3", "e6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3"]),
    ("French Defense", "C00", ["e4", "e6", "d4", "d5", "Nc3", "Nf6", "e5", "Nfd7"]),
    ("Caro-Kann Defense", "B10", ["e4", "c6", "d4", "d5", "Nc3", "dxe4", "Nxe4", "Bf5"]),
    ("Scandinavian Defense", "B01", ["e4", "d5", "exd5", "Qxd5", "Nc3", "Qa5"]),
    ("Queen's Gambit Declined", "D30", ["d4", "d5", "c4", "e6", "Nc3", "Nf6", "Bg5", "Be7"]),
    ("Slav Defense", "D10", ["d4", "d5", "c4", "c6", "Nf3", "Nf6", "Nc3", "dxc4"]),
    ("King's Indian Defense", "E60", ["d4", "Nf6", "c4", "g6", "Nc3", "Bg7", "e4", "d6"]),
    ("English, Symmetrical", "A30", ["c4", "c5", "Nf3", "Nf6", "g3", "g6"]),
]


@dataclass(slots=True)
class _BookEntry:
    """Theory recorded for a single position."""

    name: str
    eco: str
    moves: dict[str, str] = field(default_factory=dict)  # san -> uci


def _build_book(lines: list[tuple[str, str, list[str]]]) -> dict[str, _BookEntry]:
    """Replay every curated line and index the theory by position EPD."""

    book: dict[str, _BookEntry] = {}
    for name, eco, moves_san in lines:
        board = chess.Board()
        for san in moves_san:
            key = board.epd()
            move = board.parse_san(san)
            entry = book.setdefault(key, _BookEntry(name=name, eco=eco))
            entry.moves.setdefault(san, move.uci())
            board.push(move)
    return book


_BOOK: dict[str, _BookEntry] = _build_book(OPENING_LINES)


class OpeningBook:
    """Read-only lookup over the pre-built opening book."""

    @staticmethod
    def lookup(fen: str) -> OpeningExplorerResult | None:
        """Return the book theory for ``fen`` or ``None`` if it is unknown."""

        board = parse_board(fen)
        entry = _BOOK.get(board.epd())
        if entry is None:
            return None
        moves = [
            TheoryMove(uci=uci, san=san, white=0, draws=0, black=0, source="book")
            for san, uci in entry.moves.items()
        ]
        return OpeningExplorerResult(
            fen=fen,
            opening_name=entry.name,
            opening_eco=entry.eco,
            total_games=0,
            moves=moves,
            # A curated book only contains main lines, so anything it knows is
            # theory by construction.
            in_theory=True,
        )
