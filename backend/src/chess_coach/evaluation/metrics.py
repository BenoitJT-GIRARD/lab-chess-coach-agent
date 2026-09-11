"""recall@k and MRR, written out rather than imported.

Thirty lines a reader can check beat a library call they have to trust — and the one
subtlety here is not in any library anyway.

**Deduplicate before cutting at k.** An article is indexed as several chunks, so a single
opening can occupy the whole top-3. Counting chunks would inflate recall at every k and
make the ablation compare noise. The ranking is therefore reduced to distinct source files,
in order of first appearance, before any cut.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence


def dedupe_sources(sources: Iterable[str]) -> list[str]:
    """Distinct source files, in order of first appearance."""

    seen: list[str] = []
    for source in sources:
        if source not in seen:
            seen.append(source)
    return seen


def recall_at_k(ranked: Sequence[str], expected: Iterable[str], k: int) -> float:
    """1.0 if any expected source appears in the first ``k`` distinct sources."""

    top = dedupe_sources(ranked)[:k]
    return 1.0 if any(source in top for source in expected) else 0.0


def reciprocal_rank(ranked: Sequence[str], expected: Iterable[str]) -> float:
    """The inverse rank of the first expected source, or 0.0 if none is retrieved."""

    wanted = set(expected)
    for position, source in enumerate(dedupe_sources(ranked), start=1):
        if source in wanted:
            return 1.0 / position
    return 0.0


def aggregate(
    per_case: Sequence[tuple[Sequence[str], Iterable[str]]],
    ks: Sequence[int] = (1, 3, 5),
) -> dict[str, float]:
    """Mean recall at each k, mean reciprocal rank, and the sample size.

    ``n`` travels with the scores on purpose: on a set of this size an interval is wider
    than most of the differences an ablation will show, and a mean published without its
    denominator invites a conclusion the sample cannot carry.
    """

    if not per_case:
        return {"n": 0}
    scores: dict[str, float] = {"n": float(len(per_case))}
    for k in ks:
        scores[f"recall@{k}"] = sum(
            recall_at_k(ranked, expected, k) for ranked, expected in per_case
        ) / len(per_case)
    scores["mrr"] = sum(reciprocal_rank(ranked, expected) for ranked, expected in per_case) / len(
        per_case
    )
    return scores
