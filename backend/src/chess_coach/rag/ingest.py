"""Ingestion pipeline: load Wikichess articles into Milvus.

Sequential and explicit on purpose:

    1. load the Markdown articles,
    2. split them into chunks,
    3. embed every chunk,
    4. (re)create the Milvus collection and insert the vectors.
"""

from __future__ import annotations

from pathlib import Path

from chess_coach.config import Settings, get_settings
from chess_coach.rag.preprocess import build_chunks, load_articles
from chess_coach.services.embeddings import EmbeddingService
from chess_coach.services.milvus_store import MilvusStore


def ingest(
    directory: str | Path | None = None,
    *,
    settings: Settings | None = None,
    recreate: bool = True,
) -> int:
    """Run the full ingestion and return the number of indexed chunks."""

    settings = settings or get_settings()
    directory = Path(directory or settings.wikichess_dir)

    articles = load_articles(directory)
    if not articles:
        raise FileNotFoundError(f"No Wikichess article found in {directory}")
    chunks = build_chunks(articles)

    embedder = EmbeddingService(settings)
    embeddings = embedder.embed([chunk.text for chunk in chunks])

    store = MilvusStore(settings)
    store.ensure_collection(recreate=recreate)
    store.insert(chunks, embeddings)

    return len(chunks)
