"""recall@k, MRR, and the deduplication that has to happen before the cut at k.

An article is indexed as several chunks. Counting them separately would inflate recall at
every k and make the ablation compare noise instead of configurations.
"""

from __future__ import annotations

from chess_coach.evaluation.metrics import (
    aggregate,
    dedupe_sources,
    recall_at_k,
    reciprocal_rank,
)


def test_dedupe_keeps_the_first_occurrence_and_the_order() -> None:
    assert dedupe_sources(["a.md", "b.md", "a.md", "c.md"]) == ["a.md", "b.md", "c.md"]


def test_recall_is_one_when_an_expected_source_is_within_k() -> None:
    assert recall_at_k(["a.md", "b.md", "c.md"], {"c.md"}, k=3) == 1.0


def test_recall_is_zero_when_the_expected_source_falls_outside_k() -> None:
    assert recall_at_k(["a.md", "b.md", "c.md"], {"c.md"}, k=2) == 0.0


def test_recall_deduplicates_before_cutting_at_k() -> None:
    # Three chunks of one article, then the right one. Without deduplication the target
    # sits at rank 4 and recall@3 reads 0; with it, at rank 2.
    ranked = ["a.md", "a.md", "a.md", "b.md"]
    assert recall_at_k(ranked, {"b.md"}, k=3) == 1.0


def test_any_of_several_acceptable_sources_counts() -> None:
    # The corpus holds two Ruy Lopez articles; returning either is correct.
    ranked = ["wikichess/00297-ruy-lopez-spanish-opening.md"]
    expected = {
        "wikichess/00012-ruy-lopez-spanish-opening.md",
        "wikichess/00297-ruy-lopez-spanish-opening.md",
    }
    assert recall_at_k(ranked, expected, k=1) == 1.0


def test_reciprocal_rank_is_the_inverse_of_the_first_hit() -> None:
    assert reciprocal_rank(["a.md", "b.md", "c.md"], {"b.md"}) == 0.5


def test_reciprocal_rank_is_zero_when_the_target_is_absent() -> None:
    assert reciprocal_rank(["a.md", "b.md"], {"z.md"}) == 0.0


def test_aggregate_reports_each_k_and_the_sample_size() -> None:
    per_case = [
        (["a.md", "b.md"], {"a.md"}),
        (["x.md", "y.md"], {"y.md"}),
    ]
    scores = aggregate(per_case, ks=(1, 3))
    assert scores["n"] == 2
    assert scores["recall@1"] == 0.5
    assert scores["recall@3"] == 1.0
    assert scores["mrr"] == 0.75


def test_aggregate_of_an_empty_set_reports_no_score() -> None:
    assert aggregate([]) == {"n": 0}
