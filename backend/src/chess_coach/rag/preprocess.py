"""Load the Wikichess articles and split them into retrievable chunks.

Chunking matters for RAG quality: chunks that are too large dilute the relevant
passage, while chunks that are too small lose context. We split each article on
paragraph boundaries and group consecutive paragraphs up to a character budget,
keeping a small overlap so an idea split across two chunks stays retrievable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Article:
    """A single opening article of the knowledge base."""

    slug: str
    title: str
    text: str
    # Name of the folder the article was read from ("wikichess" or "openings").
    # It travels down to the chunks so a retrieved passage can be traced back
    # to its origin.
    collection: str = ""


@dataclass(slots=True)
class Chunk:
    """A retrievable passage extracted from an article."""

    chunk_id: str
    opening: str
    source: str
    text: str


def load_articles(directory: Path) -> list[Article]:
    """Read every ``*.md`` file in ``directory`` into an :class:`Article`."""

    directory = Path(directory)
    articles: list[Article] = []
    for path in sorted(directory.glob("*.md")):
        raw = path.read_text(encoding="utf-8").strip()
        articles.append(
            Article(
                slug=path.stem,
                # The title is read before cleaning, since it is the "# " heading.
                title=_extract_title(raw, fallback=path.stem),
                text=strip_markdown(raw),
                collection=directory.name,
            )
        )
    return articles


def strip_markdown(text: str) -> str:
    """Remove the Markdown markers so a passage reads as plain prose.

    The articles are stored as Markdown — a title, a quoted block of metadata,
    then section headings. Those markers are noise once a passage is shown to a
    player or handed to the language model, so they are dropped. The words
    themselves are kept: the ECO code and the move sequence help the search.
    """

    lines: list[str] = []
    for line in text.splitlines():
        line = re.sub(r"^\s{0,3}#{1,6}\s*", "", line)  # titres de section
        line = re.sub(r"^\s{0,3}>\s?", "", line)  # bloc de métadonnées
        line = line.replace("**", "").replace("__", "")  # bold
        lines.append(line.rstrip())
    # At most two newlines: the chunking splits on paragraphs.
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _extract_title(text: str, *, fallback: str) -> str:
    """Return the first level-1 Markdown heading, or ``fallback``."""

    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def _split_paragraphs(text: str) -> list[str]:
    """Split Markdown into non-empty paragraphs (blank-line separated)."""

    paragraphs = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paragraphs if p.strip()]


def chunk_text(text: str, *, max_chars: int = 600, overlap_paragraphs: int = 1) -> list[str]:
    """Group paragraphs into chunks of at most ``max_chars`` characters.

    ``overlap_paragraphs`` paragraphs are repeated at the start of the next
    chunk so context is not lost at chunk boundaries.
    """

    paragraphs = _split_paragraphs(text)
    chunks: list[str] = []
    current: list[str] = []
    length = 0

    for paragraph in paragraphs:
        if current and length + len(paragraph) > max_chars:
            chunks.append("\n\n".join(current))
            current = current[-overlap_paragraphs:] if overlap_paragraphs else []
            length = sum(len(p) for p in current)
        current.append(paragraph)
        length += len(paragraph)

    if current:
        chunks.append("\n\n".join(current))
    return chunks


def build_chunks(articles: list[Article], **chunk_kwargs: int) -> list[Chunk]:
    """Turn a list of articles into uniquely-identified chunks."""

    chunks: list[Chunk] = []
    for article in articles:
        prefix = f"{article.collection}/" if article.collection else ""
        for index, passage in enumerate(chunk_text(article.text, **chunk_kwargs)):
            chunks.append(
                Chunk(
                    chunk_id=f"{prefix}{article.slug}-{index}",
                    opening=article.title,
                    source=f"{prefix}{article.slug}.md",
                    text=passage,
                )
            )
    return chunks
