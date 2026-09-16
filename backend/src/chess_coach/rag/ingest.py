"""Ingestion pipeline: load the opening knowledge base into Milvus.

Sequential and explicit on purpose:

    1. load the Markdown articles of every knowledge folder,
    2. split them into chunks,
    3. embed every chunk,
    4. (re)create the Milvus collection and insert the vectors.

The knowledge base has two folders. ``var/wikichess`` holds the articles
downloaded from FICGS Wikichess, which are not redistributed with this project:
the folder holds nothing but its manifest until ``scripts.fetch_wikichess`` has
run. ``data/openings`` holds the complementary notes written in French for young
players. Both are indexed in the same collection, and every chunk keeps the
name of the folder it came from, so a retrieved passage can always be traced
back to its origin.
"""

from __future__ import annotations

import json
from pathlib import Path

from chess_coach.config import Settings, get_settings
from chess_coach.rag.preprocess import Article, build_chunks, load_articles
from chess_coach.services.embeddings import EmbeddingService
from chess_coach.services.milvus_store import MilvusStore
from chess_coach.utils.paths import WIKICHESS_MANIFEST


def knowledge_directories(settings: Settings) -> list[Path]:
    """Return the folders that make up the knowledge base."""

    return [Path(settings.wikichess_dir), Path(settings.openings_dir)]


def _require_downloaded_corpus(directory: Path) -> None:
    """Fail early, and say why, when the Wikichess corpus has not been downloaded.

    Indexing the eleven French notes alone would succeed, answer, and quietly score a
    third of what the measurements report.
    """

    if not WIKICHESS_MANIFEST.is_file() or any(directory.glob("*.md")):
        return
    listed = json.loads(WIKICHESS_MANIFEST.read_text(encoding="utf-8"))["articles"]
    raise FileNotFoundError(
        f"{directory} holds none of the {len(listed)} articles its manifest lists. "
        "They are not redistributed with this project: run "
        "`python -m scripts.fetch_wikichess` to download them again."
    )


def load_knowledge_base(directories: list[Path]) -> list[Article]:
    """Read every article of every folder, reporting what was found."""

    articles: list[Article] = []
    for directory in directories:
        found = load_articles(directory)
        print(f"  {directory}: {len(found)} articles")
        articles.extend(found)
    return articles


def ingest(
    directories: list[Path] | None = None,
    *,
    settings: Settings | None = None,
    recreate: bool = True,
) -> int:
    """Run the full ingestion and return the number of indexed chunks."""

    settings = settings or get_settings()
    directories = directories or knowledge_directories(settings)

    _require_downloaded_corpus(Path(settings.wikichess_dir))
    articles = load_knowledge_base(directories)
    if not articles:
        raise FileNotFoundError(f"No article found in {[str(d) for d in directories]}")
    chunks = build_chunks(articles)

    embedder = EmbeddingService(settings)
    embeddings = embedder.embed([chunk.text for chunk in chunks])

    store = MilvusStore(settings)
    store.ensure_collection(recreate=recreate)
    store.insert(chunks, embeddings)

    return len(chunks)
