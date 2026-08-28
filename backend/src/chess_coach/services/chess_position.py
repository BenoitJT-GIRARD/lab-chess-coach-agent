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
    """Return ``True`` if ``fen`` parses into a legal chess position."""

    try:
        chess.Board(fen)
    except (ValueError, IndexError):
        return False
    return True


def parse_board(fen: str) -> chess.Board:
    """Parse ``fen`` into a :class:`chess.Board`, raising on invalid input."""

    try:
        return chess.Board(fen)
    except (ValueError, IndexError) as exc:
        raise InvalidFenError(f"Invalid FEN: {fen!r}") from exc


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
