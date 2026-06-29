"""Tests for the Wikichess preprocessing (loading + chunking)."""

from __future__ import annotations

from pathlib import Path

from chess_coach.rag.preprocess import Article, build_chunks, chunk_text, load_articles

DATA_DIR = Path("data/openings")

SAMPLE = (
    "# Title\n\n"
    "Premier paragraphe assez long pour remplir un peu d'espace dans le texte.\n\n"
    "Deuxieme paragraphe tout aussi consequent afin de declencher un decoupage.\n\n"
    "Troisieme paragraphe qui ajoute encore du contenu a notre petit article.\n\n"
    "Quatrieme paragraphe pour terminer ce court exemple de chunking de texte."
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


def test_load_real_wikichess_corpus() -> None:
    articles = load_articles(DATA_DIR)

    assert len(articles) >= 10
    assert all(article.title for article in articles)
    # Titles come from the first H1 heading, not the filename.
    assert any("italienne" in article.title.lower() for article in articles)
