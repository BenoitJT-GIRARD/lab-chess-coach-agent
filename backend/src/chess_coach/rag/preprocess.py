"""Load the Wikichess articles and split them into retrievable chunks.

Chunking matters for RAG quality: chunks that are too large dilute the relevant
passage, while chunks that are too small lose context. We split each article on
paragraph boundaries and group consecutive paragraphs up to a character budget,
keeping a small overlap so an idea split across two chunks stays retrievable.

**The header block of an article is not prose, and it is not indexed.** Every article opens
on a quoted block carrying its ECO code, its first moves, a FEN and, for the downloaded ones,
a source URL and a list of contributors. Left in place it was the first thing in the first
chunk of every article: embedded with the text, so a query about strategy met a wall of codes
before a single sentence, and displayed to the player under the board. It is parsed into
fields on the :class:`Article` and dropped from the text. What the retrieval needs of it —
which opening, which file — already travels as ``opening`` and ``source``.
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
    #: What the header block carried, kept out of ``text``. None of the three is embedded:
    #: they are facts about the article, and the agent already gets the ECO code and the
    #: move order from the opening book.
    eco: str = ""
    moves: str = ""
    url: str = ""


@dataclass(slots=True)
class Chunk:
    """A retrievable passage extracted from an article."""

    chunk_id: str
    opening: str
    source: str
    text: str


#: The labels the header block uses, in both corpora, mapped to the field they fill. The
#: downloaded articles write one line per label; the notes written here put them on one line
#: separated by a middle dot. Anything else in the block — the FEN, the list of Wikichess
#: contributors — is read and dropped: it belongs to the article, not to a passage about it.
HEADER_FIELDS = {
    "code eco": "eco",
    "eco": "eco",
    "coups": "moves",
    "premiers coups": "moves",
    "source": "url",
}


def split_header(text: str) -> tuple[dict[str, str], str]:
    """Separate the quoted header block from the body, and read its labels.

    The block is the run of ``>`` lines that follows the title. Returning the body separately
    is what keeps the codes out of the embedding and out of the passage a player reads.
    """

    fields: dict[str, str] = {}
    body: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith(">"):
            body.append(line)
            continue
        for piece in re.split(r"\s+[·•]\s+", stripped.lstrip("> ").strip()):
            label, separator, value = piece.partition(":")
            if not separator:
                continue
            field = HEADER_FIELDS.get(label.strip().lower())
            if field and value.strip():
                fields.setdefault(field, value.strip())
    return fields, "\n".join(body)


def load_articles(directory: Path) -> list[Article]:
    """Read every ``*.md`` file in ``directory`` into an :class:`Article`."""

    directory = Path(directory)
    articles: list[Article] = []
    for path in sorted(directory.glob("*.md")):
        raw = path.read_text(encoding="utf-8").strip()
        fields, body = split_header(raw)
        articles.append(
            Article(
                slug=path.stem,
                # The title is read before cleaning, since it is the "# " heading.
                title=_extract_title(raw, fallback=path.stem),
                text=strip_markdown(body),
                collection=directory.name,
                eco=fields.get("eco", ""),
                moves=fields.get("moves", ""),
                url=fields.get("url", ""),
            )
        )
    return articles


def strip_markdown(text: str) -> str:
    """Remove the Markdown markers so a passage reads as plain prose.

    What is left after :func:`split_header` is a title and a series of section headings. Both
    are noise once a passage is shown to a player or handed to the language model, so the
    markers go and the words stay.
    """

    lines: list[str] = []
    for line in text.splitlines():
        line = re.sub(r"^\s{0,3}#{1,6}\s*", "", line)  # titres de section
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
