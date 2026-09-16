"""Chess position handling built on top of python-chess.

This module is the single source of truth for everything related to reading a
FEN string: validating it, listing the legal moves, and producing a compact,
human-readable description of the position.

The description mirrors the way a chess position is handed to a language model
in the Kaggle "Game Arena" experiments (board diagram + side to move + legal
moves): giving the agent this structured context is what lets it reason about
the position instead of just the raw FEN.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import chess

# Standard starting position, handy as a default and for tests.
STARTING_FEN = chess.STARTING_FEN


class InvalidFenError(ValueError):
    """Raised when a FEN string cannot be parsed into a legal position."""


@dataclass(slots=True)
class PositionInfo:
    """A structured, serialisable description of a chess position."""

    fen: str
    side_to_move: str  # "white" or "black"
    fullmove_number: int
    castling_rights: str
    is_check: bool
    is_game_over: bool
    legal_moves_san: list[str] = field(default_factory=list)
    board_ascii: str = ""


def is_valid_fen(fen: str) -> bool:
    """Return ``True`` if ``fen`` parses into a legal chess position.

    Parsing is not enough. ``chess.Board`` accepts a great deal that no game can reach — eight
    white kings on the first rank, a pawn on the eighth, the side that is not to move standing
    in check — and every one of those would travel through the coach as a position: the opening
    book would miss, the engine would return a score for it, and the answer would look like the
    answer to a real question. ``board.status()`` is what python-chess knows about that, and
    this function is the one place the repository asks it.
    """

    try:
        board = chess.Board(fen)
    except (ValueError, IndexError):
        return False
    return board.is_valid()


def parse_board(fen: str) -> chess.Board:
    """Parse ``fen`` into a :class:`chess.Board`, raising on anything a game cannot reach.

    The refusal names what python-chess found wrong, so a caller reading a log learns that the
    position had two black kings rather than that a string was rejected.
    """

    try:
        board = chess.Board(fen)
    except (ValueError, IndexError) as exc:
        raise InvalidFenError(f"Invalid FEN: {fen!r}") from exc
    if not board.is_valid():
        raise InvalidFenError(f"Invalid FEN: {fen!r} ({board.status()!r})")
    return board


def describe_position(fen: str) -> PositionInfo:
    """Build a :class:`PositionInfo` from a FEN string.

    The legal moves are returned in Standard Algebraic Notation (SAN, e.g.
    ``Nf3``) because that is the notation players read and the agent quotes.
    """

    board = parse_board(fen)
    return PositionInfo(
        fen=board.fen(),
        side_to_move="white" if board.turn == chess.WHITE else "black",
        fullmove_number=board.fullmove_number,
        castling_rights=board.castling_xfen(),
        is_check=board.is_check(),
        is_game_over=board.is_game_over(),
        legal_moves_san=[board.san(move) for move in board.legal_moves],
        board_ascii=str(board),
    )


def uci_to_san(fen: str, uci: str) -> str:
    """Translate a UCI move (e.g. ``e2e4``) into SAN (e.g. ``e4``) for a position.

    Falls back to the raw UCI string if the move is not legal in the position,
    so the caller never crashes on unexpected engine output.
    """

    board = parse_board(fen)
    try:
        move = chess.Move.from_uci(uci)
    except (ValueError, chess.InvalidMoveError):
        return uci
    if move in board.legal_moves:
        return board.san(move)
    return uci
