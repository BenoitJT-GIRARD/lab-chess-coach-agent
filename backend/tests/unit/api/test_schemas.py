"""The published contract, checked on the models rather than through a client.

`docs/api.md` and the OpenAPI page both describe these models, and the Angular client is
generated against them by hand. What follows fixes the three things a reader of a score
cannot check for themselves: whose side the evaluation is written from, that a default list
belongs to one response rather than to the class, and that the literal fields really are
closed.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from chess_coach.api.schemas import (
    AgentResponse,
    EvaluationResponse,
    HealthResponse,
    MovesResponse,
    MoveStat,
)


def test_an_evaluation_is_always_written_from_whites_side() -> None:
    """A centipawn score with no stated side is the reading error this field prevents.

    The engine returns the score from the side to move; the API republishes it from White's.
    The field is a `Literal`, so a serving layer that starts flipping it fails here.
    """
    evaluation = EvaluationResponse(
        fen="8/8/8/8/8/8/8/K6k w - - 0 1", evaluation_type="cp", value=-35, depth=12
    )

    assert evaluation.perspective == "white"

    with pytest.raises(ValidationError):
        EvaluationResponse(
            fen="8/8/8/8/8/8/8/K6k w - - 0 1",
            evaluation_type="cp",
            value=-35,
            depth=12,
            perspective="black",
        )


def test_an_unknown_evaluation_type_is_refused() -> None:
    """Two words are admitted. A third would reach the frontend and be rendered as a number."""
    with pytest.raises(ValidationError):
        EvaluationResponse(
            fen="8/8/8/8/8/8/8/K6k w - - 0 1", evaluation_type="centipawns", value=0, depth=1
        )


def test_two_answers_do_not_share_their_empty_lists() -> None:
    """The classic mutable default: one position's moves appearing under another's FEN."""
    first, second = MovesResponse(fen="a", in_theory=False), MovesResponse(fen="b", in_theory=False)

    first.moves.append(MoveStat(uci="e2e4", san="e4", white=1, draws=0, black=0, total=1))

    assert second.moves == []


def test_an_agent_answer_survives_a_state_that_holds_nothing() -> None:
    """The graph can fail before its first node, and the route still has to answer."""
    answer = AgentResponse(fen="8/8/8/8/8/8/8/K6k w - - 0 1", valid=False)

    assert answer.theory_moves == []
    assert answer.evaluation is None
    assert answer.recommendation == ""
    assert answer.error is None


def test_the_health_payload_names_its_service() -> None:
    """A liveness probe that answers "ok" and nothing else cannot say which service answered."""
    payload = HealthResponse(service="chess_coach", version="0.1.0")

    assert payload.status == "ok"
    assert payload.service == "chess_coach"
