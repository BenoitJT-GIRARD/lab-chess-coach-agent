"""The evaluation set points at articles that exist, and the served variant is the code.

A case labelled with a file the corpus does not hold is a label nothing can satisfy: it
drags recall down for good and no run will ever say why.
"""

from __future__ import annotations

import pytest

from chess_coach.evaluation.cases import corpus_sources, load_cases
from chess_coach.evaluation.variants import SERVED, VARIANTS


def test_every_case_points_at_an_article_that_exists() -> None:
    corpus = corpus_sources()
    if not corpus:
        # The articles belong to their authors and are downloaded by the reader, so a clone
        # holds none of them. `test_preprocess.py` skips on the same ground; this one asserted
        # instead, and said « every label is wrong » where it meant « there is no corpus ».
        pytest.skip("corpus not downloaded: run `python -m scripts.fetch_wikichess`")
    missing = [
        (case.id, source)
        for case in load_cases()
        for source in case.expected_sources
        if source not in corpus
    ]
    assert not missing, f"labels pointing outside the corpus: {missing}"


def test_case_ids_are_unique() -> None:
    ids = [case.id for case in load_cases()]
    assert len(ids) == len(set(ids))


def test_the_set_is_large_enough_to_be_worth_running() -> None:
    assert len(load_cases()) >= 12


def test_the_served_variant_is_the_agent_s_own_function() -> None:
    """The ablation must compare the product against alternatives, not a copy of it."""
    from chess_coach.agent.graph import build_context_query

    case = load_cases()[0]
    assert VARIANTS[SERVED](case) == build_context_query({"opening_name": case.opening_name})


def test_the_variants_produce_four_distinct_queries() -> None:
    case = load_cases()[0]
    queries = {name: build(case) for name, build in VARIANTS.items()}
    assert len(set(queries.values())) == len(VARIANTS)
