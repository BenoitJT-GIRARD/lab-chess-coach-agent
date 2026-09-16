"""The move-citation reader, on hand-made answers.

Every case here is one way the count could be wrong, and all of them in the same
direction: an invention counted where there was none is a false accusation against the
model. Three of them come from answers the real model actually wrote.
"""

from __future__ import annotations

import chess

from chess_coach.evaluation.moves import (
    cited_tokens,
    classify,
    offered_moves,
    resolve,
    summarise,
)

# After 1.e4 e5 2.Nf3 Nc6 3.Bc4: the Italian, Black to move.
ITALIAN = "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3"

PROMPT = (
    "FEN : " + ITALIAN + "\n"
    "Trait aux : black\n"
    "Coups légaux : Nf6, Bc5, d6, Be7, Nge7, a6, h6, Qf6, Qh4, b5, Na5, d5\n"
    "Ouverture : Italian Game (C50)\n"
    "Coups théoriques, avec le nombre de parties de maîtres :\n"
    "  - Nf6 (103572421 parties)\n"
    "  - Bc5 (101156348 parties)\n"
    "Coup mis en avant dans l'interface : Nf6, le plus joué en parties de maîtres.\n"
)


def texts(tokens) -> list[str]:
    return [token.text for token in tokens]


def test_the_french_notation_of_a_move_it_was_given_is_not_an_invention() -> None:
    """Handed `Nf6`, a model writing French answers `Cf6`. Same move, other language."""

    answer = "Joue Cf6 : le cavalier attaque et prépare le roque."

    citations = classify(ITALIAN, answer, PROMPT)

    assert [(c.token, c.san, c.verdict, c.notation) for c in citations] == [
        ("Cf6", "Nf6", "offered", "french")
    ]


def test_a_named_square_is_not_a_cited_move() -> None:
    """« la case f7 » is a place. As a move for Black it would not even be legal."""

    answer = "Le fou blanc en c4 vise la case f7, le point faible de la position."

    assert texts(cited_tokens(answer)) == []


def test_a_move_behind_its_number_belongs_to_the_line() -> None:
    """The presentation tells the opening's story; those moves are already played.

    Both spellings the model uses: the number for White, the ellipsis for Black.
    """

    answer = "La Caro-Kann est une réponse à 1.e4 : en jouant 1...c6, les Noirs préparent ...d5."

    verdicts = [(c.token, c.verdict) for c in classify(ITALIAN, answer, PROMPT)]

    assert verdicts == [("e4", "line"), ("c6", "line"), ("d5", "line")]


def test_the_reply_of_a_numbered_line_stays_in_the_line() -> None:
    """« commence par 1.e4 d5 » — Black's move carries no number, and is not a proposal.

    The sentence is one the model actually wrote. Read alone, `d5` is illegal here and
    would have been counted as invented.
    """

    answer = "La Défense scandinave est une ouverture qui commence par 1.e4 d5."

    assert [(c.token, c.verdict) for c in classify(ITALIAN, answer, PROMPT)] == [
        ("e4", "line"),
        ("d5", "line"),
    ]


def test_a_square_named_through_an_adjective_is_still_a_place() -> None:
    """« la case centrale e4 », « en particulier d5 » — both written by the model."""

    assert texts(cited_tokens("Les Noirs contrôlent la case centrale e4.")) == []
    assert texts(cited_tokens("Il renforce les cases centrales, en particulier d5.")) == []
    # Two words is where the filter stops: this one is a citation, not a place.
    assert texts(cited_tokens("Le fou en c4 vise f7.")) == ["f7"]


def test_a_move_that_was_not_given_is_separated_from_one_that_does_not_exist() -> None:
    answer = "Tu peux jouer h6, ou même Qh5 pour attaquer tout de suite."

    verdicts = {c.token: c.verdict for c in classify(ITALIAN, answer, PROMPT)}

    # h6 is in the twelve legal moves the prompt lists.
    assert verdicts["h6"] == "offered"
    # Qh5 is not a move of this position at all: the black queen cannot reach h5.
    assert verdicts["Qh5"] == "illegal"


def test_a_legal_move_the_prompt_left_out_is_its_own_verdict() -> None:
    """The prompt lists twelve legal moves. The thirteenth is real, and was not given."""

    answer = "Une autre idée est f5, plus rare."

    citations = classify(ITALIAN, answer, PROMPT)

    assert [(c.san, c.verdict) for c in citations] == [("f5", "legal")]
    assert "f5" not in offered_moves(chess.Board(ITALIAN), PROMPT)


def test_the_unfiltered_reading_is_an_upper_bound() -> None:
    """The filter can drop a real citation. The strict reading is published beside it.

    « le pion e4 » names a pawn here, and the filter is right to skip it — but the same
    words could cite a move, so the number that could accuse the model is published too.
    """

    answer = "Le cavalier attaque le pion e4."

    assert texts(cited_tokens(answer)) == []
    assert texts(cited_tokens(answer, strict=True)) == ["e4"]
    assert [c.verdict for c in classify(ITALIAN, answer, PROMPT, strict=True)] == ["illegal"]


def test_a_word_ending_in_a_filtered_syllable_does_not_hide_a_move() -> None:
    """`de` inside « solide » is not the preposition: the filter needs a word boundary."""

    assert texts(cited_tokens("Une position solide d5 tient le centre.")) == ["d5"]


def test_an_eco_code_is_not_a_move() -> None:
    assert texts(cited_tokens("L'ouverture italienne porte le code C50.")) == []


def test_castling_is_read_in_both_spellings() -> None:
    board = chess.Board("r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 5 4")

    assert resolve(board, "O-O")[0] == "O-O"
    assert resolve(board, "0-0")[0] == "O-O"


def test_the_summary_counts_each_verdict() -> None:
    answer = "Après 1.e4, Cf6 est le coup principal, mais f5 existe, et Qh5 n'existe pas."

    assert summarise(classify(ITALIAN, answer, PROMPT)) == {
        "cited": 4,
        "offered": 1,
        "legal_not_offered": 1,
        "illegal": 1,
        "line_reference": 1,
        "in_french_notation": 1,
    }
