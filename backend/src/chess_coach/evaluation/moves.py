"""Count the moves an answer cites, and whether the prompt had given them.

The strongest line of the system prompt is an instruction: *ne cite que les coups qui te
sont donnés, n'en invente aucun*. It is testable. Read the answer for move citations,
compare them with what the prompt actually contained, and check the rest against the
board.

Three traps make a naive count wrong, and all three inflate it — each one accuses the
model of an invention it did not commit.

*The answer is written in French, the moves are given in English.* Handed ``Nf3``, a model
writing French prose returns ``Cf3`` — the same move, the notation of its language.
Translating before comparing is the difference between measuring obedience and measuring
notation.

*French prose names squares as often as moves.* « Le fou vise la case f7 » is a location,
not a move, and for White ``f7`` is not even legal. A bare square following a positional
word is therefore not read as a move.

*A move behind a number belongs to the line, not to the position.* Asked to present the
opening, the model writes « une réponse solide à 1.e4 », « en jouant 1...c6 », « commence
par 1.e4 d5 ». Those moves have already been played; judged against the board in front of
it they are all illegal. They are recorded apart, under ``line``, and left out of the
invention count — with the limit that comes with it: what the presentation says about an
opening's history is not checked here, only what the answer proposes for the position at
hand. Black's reply carries no number of its own, so a move that follows a numbered one
with nothing but space between them belongs to the same line.

The verdicts are ``offered`` (the token is in the prompt), ``legal`` (a real move of the
position that the prompt did not give), ``illegal`` (no such move here) and ``line`` (a
move of the opening's sequence, cited behind its number).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import chess

# Piece letters in French notation, and what they are in the English SAN the prompt uses.
# `R` is the ambiguous one: roi in French, rook in English. English is tried first, so a
# token only reaches this table when it does not parse as English.
FRENCH_PIECES = {"D": "Q", "T": "R", "F": "B", "C": "N", "R": "K"}

# A move-looking token: castling, or an optional piece letter and disambiguation followed
# by a target square, with an optional promotion and check mark.
TOKEN_RE = re.compile(
    r"(?<![\w-])"
    r"(?:[O0]-[O0](?:-[O0])?"
    r"|[KQRBNPDTFC]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBNDTFC])?)"
    r"[+#]?"
    r"(?![\w-])"
)

# What precedes a bare square when the sentence names a place rather than a move: a
# location noun, a preposition, or a piece — « la case f7 », « en c4 », « le pion e4 ».
# The filter is deliberately one-sided. It can drop a citation phrased as « le pion e4 »,
# so the reports carry the unfiltered reading beside it as an upper bound; what it must
# never do is accuse the model of a move the sentence was not citing.
POSITIONAL_RE = re.compile(
    r"\b(?:case|cases|colonne|colonnes|rangée|rangées|diagonale|diagonales"
    r"|en|sur|vers|depuis|de|du|à"
    r"|pion|pions|cavalier|cavaliers|fou|fous|tour|tours|dame|dames|roi|rois"
    r"|pawn|knight|bishop|rook|queen|king)"
    # One word may sit between the noun and the square — « la case centrale e4 »,
    # « en particulier d5 ». Two would start swallowing real citations.
    r"(?:\s+[\wéèêàç]+)?"
    r"[\s,]+$",
    re.IGNORECASE,
)

# A move number or an ellipsis in front of a move: the notation of a line being told.
LINE_REFERENCE_RE = re.compile(r"(?:\d+\s*\.{1,3}|\.{3})\s*$")

# What separates two moves of the same line: « 1.e4 d5 », « 1.d4 Nf6 2.c4 ». Black's
# reply carries no number of its own, so it inherits the reference from the move before.
LINE_CONTINUATION_RE = re.compile(r"^(?:\s+|\s*\d+\s*\.{1,3}\s*)$")

BARE_SQUARE_RE = re.compile(r"^[a-h][1-8]$")


@dataclass(frozen=True, slots=True)
class Token:
    """A move-looking token, and whether it was written as part of a line."""

    text: str
    line_reference: bool


@dataclass(frozen=True, slots=True)
class Citation:
    """One move cited by the answer, and what it turned out to be."""

    token: str
    san: str | None
    verdict: str
    notation: str


def cited_tokens(text: str, *, strict: bool = False) -> list[Token]:
    """Every move-looking token of ``text``, in order.

    ``strict`` keeps the bare squares that read as places rather than moves. It is the
    upper bound of what the answer could be accused of citing.
    """

    tokens: list[Token] = []
    previous_end = -1
    previous_was_line = False
    for match in TOKEN_RE.finditer(text):
        before = text[: match.start()]
        token = match.group(0)
        if not strict and BARE_SQUARE_RE.match(token) and POSITIONAL_RE.search(before):
            continue
        continues_line = previous_was_line and bool(
            LINE_CONTINUATION_RE.match(text[previous_end : match.start()])
        )
        is_line = continues_line or bool(LINE_REFERENCE_RE.search(before))
        tokens.append(Token(token, is_line))
        previous_end, previous_was_line = match.end(), is_line
    return tokens


def resolve(board: chess.Board, token: str) -> tuple[str | None, str]:
    """Read one token as a move of ``board``: its English SAN, and which notation it used.

    English first, because that is what the prompt speaks and because `R` means two
    different pieces in the two languages.
    """

    normalised = token.replace("0", "O") if token.startswith("0") else token
    try:
        return board.san(board.parse_san(normalised)), "english"
    except (chess.InvalidMoveError, chess.IllegalMoveError, chess.AmbiguousMoveError):
        pass

    head, rest = normalised[:1], normalised[1:]
    if head in FRENCH_PIECES and rest:
        try:
            move = board.parse_san(FRENCH_PIECES[head] + rest)
        except (chess.InvalidMoveError, chess.IllegalMoveError, chess.AmbiguousMoveError):
            return None, ""
        return board.san(move), "french"
    return None, ""


def offered_moves(board: chess.Board, prompt: str) -> set[str]:
    """The moves the prompt puts in front of the model, as English SAN.

    Read from the prompt itself rather than from the state, so that whatever a node adds
    later — a passage quoting a line, a move named in an article — counts as given. The
    question is what the model was shown, not what we meant to show it.
    """

    offered = set()
    for token in cited_tokens(prompt):
        san, _ = resolve(board, token.text)
        if san:
            offered.add(san)
    return offered


def classify(fen: str, answer: str, prompt: str, *, strict: bool = False) -> list[Citation]:
    """Every move cited by ``answer``, judged against ``prompt`` and against the board."""

    board = chess.Board(fen)
    offered = offered_moves(board, prompt)

    citations = []
    for token in cited_tokens(answer, strict=strict):
        san, notation = resolve(board, token.text)
        if token.line_reference:
            citations.append(Citation(token.text, san, "line", notation))
        elif san is None:
            citations.append(Citation(token.text, None, "illegal", ""))
        elif san in offered:
            citations.append(Citation(token.text, san, "offered", notation))
        else:
            citations.append(Citation(token.text, san, "legal", notation))
    return citations


def summarise(citations: list[Citation]) -> dict[str, int]:
    """Count the citations by verdict, plus how many needed the French reading."""

    return {
        "cited": len(citations),
        "offered": sum(1 for c in citations if c.verdict == "offered"),
        "legal_not_offered": sum(1 for c in citations if c.verdict == "legal"),
        "illegal": sum(1 for c in citations if c.verdict == "illegal"),
        "line_reference": sum(1 for c in citations if c.verdict == "line"),
        "in_french_notation": sum(1 for c in citations if c.notation == "french"),
    }
