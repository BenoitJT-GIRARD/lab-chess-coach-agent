"""The position route, called as the function it is.

`get_position` builds its answer with ``PositionResponse(**asdict(describe_position(fen)))``.
That line is a silent contract between a dataclass in the services layer and a Pydantic model
in the API layer: a field renamed on one side raises a `TypeError` at request time and
nowhere earlier. The first test below is that contract, written down.
"""

from __future__ import annotations

from dataclasses import fields

import pytest
from fastapi import HTTPException

from chess_coach.api.routes.position import get_position
from chess_coach.api.schemas import PositionResponse
from chess_coach.services.chess_position import STARTING_FEN, PositionInfo

#: The Ruy Lopez after 3.Bb5, the position the README shows.
RUY_LOPEZ = "r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3"


def test_the_service_dataclass_and_the_published_model_carry_the_same_fields() -> None:
    """One `asdict` away from each other, so a rename on either side has to be a rename on both."""
    assert {field.name for field in fields(PositionInfo)} == set(PositionResponse.model_fields)


def test_the_starting_position_is_described_without_any_service() -> None:
    answer = get_position(STARTING_FEN)

    assert answer.side_to_move == "white"
    assert answer.fullmove_number == 1
    assert len(answer.legal_moves_san) == 20
    assert answer.is_check is False


def test_a_position_reached_by_black_is_read_from_blacks_side() -> None:
    """Whose turn it is comes from the FEN, not from the move number."""
    answer = get_position(RUY_LOPEZ)

    assert answer.side_to_move == "black"
    assert "a6" in answer.legal_moves_san


def test_an_unparsable_fen_is_refused_with_the_string_it_was_given() -> None:
    """422 rather than 500, and the offending string in the message: the caller mistyped it."""
    with pytest.raises(HTTPException) as refusal:
        get_position("8/8/8/8/8/8/8/KKKKKKKK w - - 0 1")

    assert refusal.value.status_code == 422
    assert "KKKKKKKK" in str(refusal.value.detail)
