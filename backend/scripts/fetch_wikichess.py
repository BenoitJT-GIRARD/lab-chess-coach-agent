"""Download the opening articles of Wikichess (FICGS).

Wikichess (https://ficgs.com/wikichess.html) is the collaborative opening
repertoire this corpus is built from. It is organised as a tree of positions:
article
0 is the starting position, and every article links to the articles reached by
playing one more move. An article carries an ECO code, an opening name, an
explanatory text written by contributors, and the statistics of the games
played from that position.

The tree holds 260 000 articles, the vast majority of which are empty. Rather
than crawling it blindly, this script walks the main lines of the classical
openings — the same lines the local opening book is built from — and keeps
every documented article met along the way. Following a line with python-chess
also gives us, for free, the move sequence and the FEN of each article.

The articles themselves are not redistributed; `docs/data-source.md` quotes the
clause that forbids it. What the repository keeps of the corpus is the manifest
this script writes — which files a download produces, and where
each one comes from — so the evaluation labels can be checked without the
articles being there.

Usage (from the ``backend/`` folder)::

    python -m scripts.fetch_wikichess
"""

from __future__ import annotations

import argparse
import html
import json
import re
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import chess
import httpx

from chess_coach.services.opening_book import OPENING_LINES
from chess_coach.utils.paths import WIKICHESS_DIR, WIKICHESS_MANIFEST

BASE_URL = "https://ficgs.com/wikichess_{article_id}.html"

# A meaningful User-Agent and a pause between requests: we are a guest on this
# site, and the whole corpus is downloaded once.
USER_AGENT = "chess_coach-ffe-poc/0.1 (educational project)"
PAUSE_BETWEEN_REQUESTS = 1.5

# Articles shorter than this carry no real explanation (only the automatic
# statistics block), so they are not worth indexing.
MIN_TEXT_LENGTH = 400

# The separator Wikichess puts between the article text and its footer.
FOOTER_SEPARATOR = "============"

# The index of the corpus, written beside the articles and versioned in their place.
MANIFEST_ABOUT = (
    "Index of the Wikichess corpus. The articles themselves are not redistributed, for "
    "the licence reason docs/data-source.md sets out. Run "
    "`python -m scripts.fetch_wikichess` to download them again into `backend/var/`, "
    "which git ignores."
)


@dataclass(slots=True)
class WikichessArticle:
    """One Wikichess article, already parsed and cleaned."""

    article_id: int
    moves_san: list[str]
    fen: str
    eco: str | None
    opening: str | None
    text: str
    contributors: str
    children: list[tuple[str, int]] = field(default_factory=list)

    @property
    def url(self) -> str:
        """Public URL of the article on FICGS."""

        return BASE_URL.format(article_id=self.article_id)

    @property
    def move_line(self) -> str:
        """The move sequence written the way a chess book would (1.e4 c5)."""

        parts: list[str] = []
        for index, move in enumerate(self.moves_san):
            if index % 2 == 0:
                parts.append(f"{index // 2 + 1}.{move}")
            else:
                parts.append(move)
        return " ".join(parts)


# --------------------------------------------------------------------------
# 1. Download
# --------------------------------------------------------------------------


def download(article_id: int, client: httpx.Client) -> str:
    """Fetch one article and return its HTML source.

    Wikichess pages are served as ISO-8859-1, so the bytes are decoded
    explicitly rather than trusting the response encoding.
    """

    response = client.get(BASE_URL.format(article_id=article_id))
    response.raise_for_status()
    return response.content.decode("iso-8859-1", errors="replace")


# --------------------------------------------------------------------------
# 2. Parsing — one small function per piece of information
# --------------------------------------------------------------------------


def extract_eco(source: str) -> str | None:
    """Read the ECO code, written as ``[ECO "B20"]``."""

    match = re.search(r'\[ECO "([^"]*)"\]', source)
    return match.group(1).strip() or None if match else None


def extract_opening(source: str) -> str | None:
    """Read the opening name, written as ``[Opening "Sicilian defense"]``."""

    match = re.search(r'\[Opening "([^"]*)"\]', source)
    return html.unescape(match.group(1)).strip() or None if match else None


def extract_contributors(source: str) -> str:
    """Read the list of contributors credited at the end of the article."""

    match = re.search(r"Contributors\s*:\s*([^<]*)", source)
    return html.unescape(match.group(1)).strip() if match else ""


def _html_to_text(fragment: str) -> str:
    """Turn an HTML fragment into plain text, keeping the paragraph breaks."""

    text = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    # Collapse the spaces inside a line, but keep the empty lines that separate
    # paragraphs: the chunker relies on them.
    lines = [re.sub(r"[ \t\r]+", " ", line).strip() for line in text.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def extract_text(source: str) -> str:
    """Return the explanatory text of the article, without its footer."""

    body = re.search(r'<div align="justify">(.*?)</div>', source, re.S)
    if not body:
        return ""
    text = _html_to_text(body.group(1))
    # Everything after the separator is the automatic footer (contributors,
    # ECO tag and game statistics), which we store separately.
    return text.split(FOOTER_SEPARATOR)[0].strip()


def extract_children(source: str, board: chess.Board) -> list[tuple[str, int]]:
    """Return the ``(move, article_id)`` continuations listed on the page.

    A Wikichess page links to many other pages (navigation, the ``back`` link,
    the footer). We keep a link only when its label is a legal move in the
    current position — which is exactly the definition of a continuation.
    """

    children: list[tuple[str, int]] = []
    seen: set[str] = set()
    for article_id, label in re.findall(
        r'<a href="wikichess_(\d+)\.html"[^>]*>([^<]*)</a>', source
    ):
        # Wikichess appends "!" or "?" to comment on a move; strip them.
        move_san = label.replace("!", "").replace("?", "").strip()
        if not move_san or move_san in seen:
            continue
        try:
            board.parse_san(move_san)
        except (chess.IllegalMoveError, chess.InvalidMoveError, chess.AmbiguousMoveError):
            continue
        seen.add(move_san)
        children.append((move_san, int(article_id)))
    return children


def parse(article_id: int, source: str, moves_san: list[str]) -> WikichessArticle:
    """Assemble a :class:`WikichessArticle` from the page and its move path."""

    board = chess.Board()
    for move in moves_san:
        board.push_san(move)

    return WikichessArticle(
        article_id=article_id,
        moves_san=list(moves_san),
        fen=board.fen(),
        eco=extract_eco(source),
        opening=extract_opening(source),
        text=extract_text(source),
        contributors=extract_contributors(source),
        children=extract_children(source, board),
    )


# --------------------------------------------------------------------------
# 3. Walk the tree
# --------------------------------------------------------------------------


def is_worth_keeping(article: WikichessArticle) -> bool:
    """Decide whether an article deserves a place in the knowledge base.

    Two conditions. It must name an opening — article 0 presents the site
    itself, not a position. And it must carry a real explanation: most articles
    are only an automatic statistics block written by nobody.
    """

    return bool(article.opening) and len(article.text) >= MIN_TEXT_LENGTH


def follow_line(
    client: httpx.Client,
    moves_san: list[str],
    *,
    cache: dict[int, str],
    kept: dict[int, WikichessArticle],
) -> None:
    """Walk one opening line, article by article, from the starting position.

    At every step we are on a Wikichess article and we look, among the
    continuations it lists, for the next move of the line. If the line is not
    covered by Wikichess we simply stop there.
    """

    article_id = 0
    played: list[str] = []

    for move_san in [*moves_san, None]:
        if article_id not in cache:
            cache[article_id] = download(article_id, client)
            time.sleep(PAUSE_BETWEEN_REQUESTS)

        article = parse(article_id, cache[article_id], played)
        if article.article_id not in kept and is_worth_keeping(article):
            kept[article.article_id] = article
            print(f"  kept    #{article.article_id:<6} {article.move_line} — {article.opening}")

        if move_san is None:
            return

        next_id = next((cid for move, cid in article.children if move == move_san), None)
        if next_id is None:
            print(f"  stopped after {article.move_line or '(start)'}: no {move_san} from here")
            return

        article_id = next_id
        played.append(move_san)


def collect(client: httpx.Client, lines: list[list[str]]) -> list[WikichessArticle]:
    """Walk every line and return the documented articles, without duplicates."""

    cache: dict[int, str] = {}
    kept: dict[int, WikichessArticle] = {}

    for index, moves_san in enumerate(lines, start=1):
        print()
        print(f"Line {index}/{len(lines)}: {' '.join(moves_san)}")
        follow_line(client, moves_san, cache=cache, kept=kept)

    return sorted(kept.values(), key=lambda article: article.article_id)


# --------------------------------------------------------------------------
# 4. Write the Markdown files
# --------------------------------------------------------------------------


def slugify(value: str) -> str:
    """Turn an opening name into a safe file name."""

    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-") or "article"


def to_markdown(article: WikichessArticle) -> str:
    """Render one article as the Markdown document that will be indexed."""

    title = article.opening or f"Wikichess article {article.article_id}"
    header = [f"# {title}", ""]
    if article.eco:
        header.append(f"> Code ECO : {article.eco}")
    if article.move_line:
        header.append(f"> Coups : {article.move_line}")
    header.append(f"> FEN : {article.fen}")
    header.append(f"> Source : {article.url}")
    if article.contributors:
        header.append(f"> Contributeurs Wikichess : {article.contributors}")
    header.append("")
    return "\n".join(header) + "\n" + article.text + "\n"


def write_articles(articles: list[WikichessArticle], directory: Path) -> None:
    """Write every article into ``directory`` as a Markdown file."""

    directory.mkdir(parents=True, exist_ok=True)
    for article in articles:
        name = f"{article.article_id:05d}-{slugify(article.opening or '')}.md"
        # newline="" keeps the Unix line endings the repository uses,
        # whatever operating system the download is run on.
        with (directory / name).open("w", encoding="utf-8", newline="") as handle:
            handle.write(to_markdown(article))


def build_manifest(directory: Path, *, downloaded: str) -> dict:
    """Index the articles of ``directory``, read back from their own headers.

    Reading the files rather than the objects that produced them keeps one code path:
    the same function indexes a fresh download and the corpus already on disk.
    """

    articles = []
    for path in sorted(directory.glob("*.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        title = lines[0][2:].strip() if lines and lines[0].startswith("# ") else path.stem
        header: dict[str, str] = {}
        for line in lines[1:]:
            if not line.startswith(">"):
                if header:
                    break
                continue
            key, _, value = line[1:].strip().partition(" : ")
            header[key] = value.strip()
        articles.append(
            {
                "file": path.name,
                "article_id": int(path.name.split("-", 1)[0]),
                "opening": title,
                "eco": header.get("Code ECO", ""),
                "moves": header.get("Coups", ""),
                "url": header.get("Source", ""),
            }
        )
    return {
        "about": MANIFEST_ABOUT,
        "source": "https://ficgs.com/wikichess.html",
        "downloaded": downloaded,
        "articles": articles,
    }


def write_manifest(directory: Path, *, downloaded: str, output: Path | None = None) -> Path:
    """Index the articles of ``directory``, write that index, and return where it went.

    The index is published and the articles are not. The corpus goes to `var/`, where git
    does not keep it, while a list of titles, ECO codes and URLs records what was read.

    ``output`` defaults to the published path. A caller indexing some other directory says
    where the result goes, because a function that always wrote to the published file would
    let a test overwrite it.
    """

    path = output or WIKICHESS_MANIFEST
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        json.dump(
            build_manifest(directory, downloaded=downloaded), handle, ensure_ascii=False, indent=2
        )
        handle.write("\n")
    return path


# --------------------------------------------------------------------------
# 5. Entry point
# --------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Download the Wikichess corpus.")
    parser.add_argument("--out", type=Path, default=WIKICHESS_DIR, help="output folder")
    args = parser.parse_args()

    # The lines followed are the local opening book's, so both sources of knowledge
    # cover exactly the same repertoire.
    lines = [moves_san for _, _, moves_san in OPENING_LINES]

    print(f"Walking {len(lines)} opening lines on Wikichess...")
    with httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=30.0,
        follow_redirects=True,
    ) as client:
        articles = collect(client, lines)

    write_articles(articles, args.out)
    manifest = write_manifest(args.out, downloaded=date.today().isoformat())
    print()
    print(f"{len(articles)} articles written to {args.out}/")
    print(f"manifest written to {manifest}")


if __name__ == "__main__":
    main()
