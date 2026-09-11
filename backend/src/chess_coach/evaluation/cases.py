"""The retrieval evaluation set, and the label that makes it scorable without a judge.

Each case names the article the knowledge base should return. That name is the label:
hard, checkable, and free. No model grades anything here.

Several files can be right for one opening — the corpus holds two Ruy Lopez articles and
a French note on the same opening — so the label is a *set*. Picking one of them
arbitrarily would penalise a retrieval that returned the other, which is not a defect.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from chess_coach.config import get_settings

DEFAULT_PATH = Path("data/eval/retrieval_cases.json")


@dataclass(frozen=True, slots=True)
class RetrievalCase:
    """One question, and the articles that answer it."""

    id: str
    opening_name: str
    eco: str
    question: str
    expected_sources: tuple[str, ...]


def load_cases(path: Path | None = None) -> list[RetrievalCase]:
    """Read the evaluation set from disk."""

    payload = json.loads((path or DEFAULT_PATH).read_text(encoding="utf-8"))
    return [
        RetrievalCase(
            id=case["id"],
            opening_name=case["opening_name"],
            eco=case["eco"],
            question=case["question"],
            expected_sources=tuple(case["expected_sources"]),
        )
        for case in payload["cases"]
    ]


def corpus_sources(settings=None) -> set[str]:
    """Every ``folder/file.md`` the knowledge base can return.

    Used by the tests: a case pointing at a file that is not in the corpus is a label
    nothing can ever satisfy, and it would silently drag recall down for good.

    The Wikichess articles are not redistributed, so their folder holds nothing but its
    manifest until ``scripts.fetch_wikichess`` has run. The manifest lists exactly what
    the download writes, which is what the labels are checked against; the files
    themselves are added when they are there.
    """

    settings = settings or get_settings()
    found: set[str] = set()
    for folder in (settings.wikichess_dir, settings.openings_dir):
        directory = Path(folder)
        if not directory.is_dir():
            continue
        manifest = directory / "MANIFEST.json"
        if manifest.is_file():
            listed = json.loads(manifest.read_text(encoding="utf-8"))
            found.update(f"{directory.name}/{a['file']}" for a in listed["articles"])
        for article in sorted(directory.glob("*.md")):
            found.add(f"{directory.name}/{article.name}")
    return found
