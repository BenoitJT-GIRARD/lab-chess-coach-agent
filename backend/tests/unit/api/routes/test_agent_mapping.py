"""`agent_answer`: the state the graph leaves behind, turned into what a reader receives.

The mapping is where the two halves of the answer come apart. A failed node writes nothing
at all into the state, while the published model has a value for every field. What has to
come out of a half-finished run is an answer with a hole in it: no crash, and no default
nobody decided.

Nothing here runs the graph. The state is written by hand, which is the only way to say what
a half-finished run looks like.
"""

from __future__ import annotations

from chess_coach.api.mapping import agent_answer

FEN = "r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3"


def test_a_run_that_never_started_still_answers() -> None:
    """Every service was unreachable and the first node set an error. The caller gets a shape."""
    answer = agent_answer(FEN, {"valid": True, "error": "Milvus unreachable"})

    assert answer.fen == FEN
    assert answer.error == "Milvus unreachable"
    assert answer.theory_moves == []
    assert answer.videos == []
    assert answer.evaluation is None
    assert answer.recommendation == ""


def test_an_invalid_position_is_reported_as_invalid_and_not_as_an_error() -> None:
    """A FEN the board refuses is a fact about the request, not a failure of a source."""
    answer = agent_answer("not-a-fen", {})

    assert answer.valid is False
    assert answer.error is None
    assert answer.sources_used == []


def test_the_sources_the_run_used_are_the_ones_it_reports() -> None:
    """`sources_used` is what the answer cites. A node that answered without one is a claim."""
    state = {
        "valid": True,
        "in_theory": True,
        "total_games": 51234,
        "sources_used": ["lichess", "book"],
    }

    answer = agent_answer(FEN, state)

    assert answer.sources_used == ["lichess", "book"]
    assert answer.total_games == 51234


def test_each_nested_record_is_rebuilt_as_its_own_model() -> None:
    """The nodes hand back plain dictionaries; what leaves the API is validated."""
    state = {
        "valid": True,
        "theory_moves": [
            {"uci": "a7a6", "san": "a6", "white": 9, "draws": 3, "black": 7, "total": 19}
        ],
        "evaluation": {"fen": FEN, "evaluation_type": "cp", "value": 24, "depth": 15},
        "passages": [
            {
                "text": "The Morphy Defence",
                "opening": "Ruy Lopez",
                "source": "wikichess",
                "score": 0.81,
            }
        ],
        "videos": [
            {
                "video_id": "abc123",
                "title": "The Ruy Lopez",
                "channel": "a channel",
                "url": "https://example.invalid/watch",
                "thumbnail": "https://example.invalid/thumb.jpg",
            }
        ],
    }

    answer = agent_answer(FEN, state)

    assert answer.theory_moves[0].san == "a6"
    assert answer.evaluation is not None
    assert answer.evaluation.perspective == "white"
    assert answer.passages[0].opening == "Ruy Lopez"
    assert answer.videos[0].video_id == "abc123"
