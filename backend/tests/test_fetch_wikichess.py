"""Tests for the Wikichess downloader.

Only the parsing is tested, on a fixture that reproduces the markup of a page with
invented text: the network is never touched, and nothing FICGS wrote is stored here.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.fetch_wikichess import (
    WikichessArticle,
    is_worth_keeping,
    parse,
    to_markdown,
    write_articles,
    write_manifest,
)

FIXTURE = Path(__file__).parent / "fixtures" / "wikichess_article.html"

# The page is the position after 1.e4 c5, so the walk reached it with those moves.
MOVES = ["e4", "c5"]


def load_fixture() -> str:
    """Read the saved page the way the downloader reads a live one."""

    return FIXTURE.read_bytes().decode("iso-8859-1")


def test_parse_reads_the_opening_and_its_eco_code() -> None:
    article = parse(3, load_fixture(), MOVES)

    assert article.opening == "Sicilian defense"
    assert article.eco == "B20"
    assert article.contributors == "Ada Example, Blaise Testeur"


def test_parse_keeps_only_the_explanatory_text() -> None:
    article = parse(3, load_fixture(), MOVES)

    assert article.text.startswith("The Sicilian Defence")
    # The footer (contributors, ECO tag, game statistics) is cut off.
    assert "Contributors" not in article.text
    assert "games, White ELO" not in article.text
    # Paragraph breaks survive, because the chunker splits on them.
    assert "\n\n" in article.text
    # HTML entities are decoded.
    assert "Black's c-pawn" in article.text


def test_parse_computes_the_position_and_the_move_line() -> None:
    article = parse(3, load_fixture(), MOVES)

    assert article.move_line == "1.e4 c5"
    assert article.fen == "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"


def test_children_are_the_legal_continuations_only() -> None:
    article = parse(3, load_fixture(), MOVES)

    assert article.children == [("Nf3", 6), ("Nc3", 7), ("f4", 153)]
    # The "back" link is not a move, so it is not followed.
    assert all(move != "back" for move, _ in article.children)


def test_to_markdown_credits_the_source() -> None:
    document = to_markdown(parse(3, load_fixture(), MOVES))

    assert document.startswith("# Sicilian defense")
    assert "https://ficgs.com/wikichess_3.html" in document
    assert "B20" in document
    assert "Ada Example" in document


def test_the_manifest_indexes_what_the_download_writes(tmp_path: Path) -> None:
    """The articles are not redistributed, so the manifest is what the repository keeps.

    It is written from the files themselves, so a download and the corpus already on
    disk go through the same code.
    """

    write_articles([parse(3, load_fixture(), MOVES)], tmp_path)
    manifest = write_manifest(tmp_path, downloaded="2026-09-08")

    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["downloaded"] == "2026-09-08"
    assert payload["articles"] == [
        {
            "file": "00003-sicilian-defense.md",
            "article_id": 3,
            "opening": "Sicilian defense",
            "eco": "B20",
            "moves": "1.e4 c5",
            "url": "https://ficgs.com/wikichess_3.html",
        }
    ]


def test_an_article_without_explanation_is_dropped() -> None:
    empty = WikichessArticle(
        article_id=6701,
        moves_san=["e4", "Na6"],
        fen="r1bqkbnr/pppppppp/n7/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 1 2",
        eco="B00",
        opening="Lemming defense",
        text="",
        contributors="Benjamin Block",
    )

    assert is_worth_keeping(empty) is False
    assert is_worth_keeping(parse(3, load_fixture(), MOVES)) is True
