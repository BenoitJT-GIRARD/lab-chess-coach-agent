"""The sweep obeys the arithmetic the routing rule imposes.

A sweep that let a raised threshold put *more* positions in theory would be measuring its
own bug, and the curve it published would look just as plausible.
"""

from __future__ import annotations

from chess_coach.evaluation.threshold import is_in_theory, plateau_around, sweep

POSITIONS = [
    {"name": "main line", "total_games": 50_000, "n_moves": 12},
    {"name": "side line", "total_games": 1_500, "n_moves": 8},
    {"name": "rare line", "total_games": 120, "n_moves": 3},
    {"name": "curiosity", "total_games": 20, "n_moves": 1},
    {"name": "never played", "total_games": 0, "n_moves": 0},
]


def test_a_position_with_no_moves_is_never_theory() -> None:
    """The served rule is `moves and total_games >= threshold`, not the count alone."""
    assert is_in_theory({"total_games": 10**6, "n_moves": 0}, threshold=1) is False


def test_raising_the_threshold_never_adds_positions_to_theory() -> None:
    rows = sweep(POSITIONS, [0, 100, 1_000, 10_000, 100_000])
    counts = [row["in_theory"] for row in rows]
    assert counts == sorted(counts, reverse=True)


def test_the_flip_count_matches_the_difference_between_two_steps() -> None:
    rows = sweep(POSITIONS, [0, 1_000])
    assert rows[0]["in_theory"] == 4  # everything but the position with no moves
    assert rows[1]["in_theory"] == 2  # main line and side line
    assert rows[1]["flipped"] == 2


def test_the_first_row_has_nothing_to_flip_against() -> None:
    assert sweep(POSITIONS, [500])[0]["flipped"] == 0


def test_in_theory_and_out_of_theory_always_add_up() -> None:
    for row in sweep(POSITIONS, [0, 100, 5_000]):
        assert row["in_theory"] + row["out_of_theory"] == len(POSITIONS)


def test_plateau_reports_movement_on_both_sides() -> None:
    room = plateau_around(POSITIONS, threshold=1_000, factor=10)
    # Dividing by ten lets the 120-game line in; multiplying by ten drops the 1 500 one.
    assert room["flipped_if_divided"] == 1
    assert room["flipped_if_multiplied"] == 1
    assert room["n"] == len(POSITIONS)
