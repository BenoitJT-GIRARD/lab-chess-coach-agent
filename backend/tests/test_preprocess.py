"""Tests for the knowledge-base preprocessing (loading + chunking)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from chess_coach.rag.preprocess import (
    Article,
    build_chunks,
    chunk_text,
    load_articles,
    strip_markdown,
)

WIKICHESS_DIR = Path("data/wikichess")
OPENINGS_DIR = Path("data/openings")

SAMPLE = (
    "# Title\n\n"
    "Premier paragraphe assez long pour remplir un peu d'espace dans le texte.\n\n"
    "Deuxieme paragraphe tout aussi consequent afin de declencher un decoupage.\n\n"
    "Troisieme paragraphe qui ajoute encore du contenu a notre petit article.\n\n"
    "Quatrieme paragraphe pour terminer ce court exemple de chunking de texte."
)

ARTICLE_MARKDOWN = (
    "# Sicilian defense\n"
    "\n"
    "> Code ECO : B20\n"
    "> Coups : 1.e4 c5\n"
    "\n"
    "## Idees principales\n"
    "\n"
    "Les Noirs contestent le centre **immediatement**.\n"
)


def test_chunk_text_respects_budget_and_overlaps() -> None:
    chunks = chunk_text(SAMPLE, max_chars=140, overlap_paragraphs=1)

    assert len(chunks) >= 2
    # No chunk should be wildly over budget (a single paragraph may exceed it).
    assert all(len(chunk) <= 300 for chunk in chunks)
    # Overlap: the last paragraph of a chunk reappears at the start of the next.
    first_tail = chunks[0].split("\n\n")[-1]
    assert first_tail in chunks[1]


def test_build_chunks_creates_unique_ids() -> None:
    articles = [Article(slug="italienne", title="Italienne", text=SAMPLE)]

    chunks = build_chunks(articles, max_chars=140)

    ids = [chunk.chunk_id for chunk in chunks]
    assert len(ids) == len(set(ids))
    assert all(chunk.opening == "Italienne" for chunk in chunks)
    assert all(chunk.source == "italienne.md" for chunk in chunks)


def test_build_chunks_prefixes_the_source_with_its_collection() -> None:
    articles = [
        Article(slug="00003-sicilian", title="Sicilian", text=SAMPLE, collection="wikichess")
    ]

    chunks = build_chunks(articles, max_chars=140)

    assert all(chunk.source == "wikichess/00003-sicilian.md" for chunk in chunks)
    assert all(chunk.chunk_id.startswith("wikichess/00003-sicilian-") for chunk in chunks)


def test_strip_markdown_keeps_the_words_and_drops_the_markers() -> None:
    nettoye = strip_markdown(ARTICLE_MARKDOWN)

    assert "#" not in nettoye
    assert ">" not in nettoye
    assert "**" not in nettoye
    # The words stay: the ECO code and the move line both help retrieval.
    assert "Sicilian defense" in nettoye
    assert "Code ECO : B20" in nettoye
    assert "immediatement" in nettoye


def test_load_the_french_opening_notes() -> None:
    articles = load_articles(OPENINGS_DIR)

    assert len(articles) >= 10
    assert all(article.title for article in articles)
    # Titles come from the first H1 heading, not the filename.
    assert any("italienne" in article.title.lower() for article in articles)
    assert all(article.collection == "openings" for article in articles)


def test_the_manifest_indexes_the_corpus() -> None:
    """The articles are not redistributed; their index is what the repository holds.

    Without it nothing would say which corpus the published measurements were taken on,
    and the evaluation labels would point at files no one could name.
    """

    payload = json.loads((WIKICHESS_DIR / "MANIFEST.json").read_text(encoding="utf-8"))

    assert len(payload["articles"]) == 21
    assert all(article["file"].endswith(".md") for article in payload["articles"])
    assert all(
        article["url"].startswith("https://ficgs.com/wikichess_") for article in payload["articles"]
    )


@pytest.mark.skipif(
    not any(WIKICHESS_DIR.glob("*.md")),
    reason="corpus not downloaded: run `python -m scripts.fetch_wikichess`",
)
def test_load_the_wikichess_corpus() -> None:
    articles = load_articles(WIKICHESS_DIR)

    assert len(articles) >= 10
    assert all(article.collection == "wikichess" for article in articles)
    # Every downloaded article credits the page it came from.
    assert all("ficgs.com/wikichess_" in article.text for article in articles)
    # And the Markdown markers are gone by the time the text is indexed.
    assert all(not article.text.startswith("#") for article in articles)
