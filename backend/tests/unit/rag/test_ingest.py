"""Ingestion, with a fake embedder and a fake store.

The pipeline itself is four steps and no arithmetic, which is exactly why it is worth
testing: the failures it can have are all of the kind that succeed. An index built on eleven
French notes because the downloaded corpus was missing answers every question and scores a
third of what the measurements report; a vector attached to the wrong passage retrieves
plausible text for the wrong opening. Neither raises.

Nothing here embeds anything or reaches a database. What is under test is the order of the
steps and what each one is handed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from chess_coach.rag import ingest as ingest_module
from chess_coach.rag.ingest import ingest, knowledge_directories, load_knowledge_base

ARTICLE = """# The Ruy Lopez

> ECO C60. 1.e4 e5 2.Nf3 Nc6 3.Bb5

White attacks the knight that defends the pawn on e5. Black answers 3...a6 in the great
majority of master games, and the bishop retreats to a4 rather than taking on c6.

The resulting positions are slow. Both sides castle, and the fight is about the centre
rather than about an early attack on the king.
"""


@dataclass
class FakeEmbedder:
    """Returns one vector per text, each carrying the length of the text it came from."""

    seen: list[list[str]] = field(default_factory=list)

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.seen.append(list(texts))
        return [[float(len(text)), 0.0] for text in texts]


@dataclass
class FakeStore:
    """Records what it was asked to create and what it was handed to insert."""

    recreated: list[bool] = field(default_factory=list)
    rows: list[tuple[str, str, list[float]]] = field(default_factory=list)

    def ensure_collection(self, *, recreate: bool = False) -> None:
        self.recreated.append(recreate)

    def insert(self, chunks, embeddings) -> int:
        self.rows = [
            (chunk.chunk_id, chunk.text, embedding)
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]
        return len(self.rows)


@dataclass
class FakeSettings:
    """Only the three fields the ingestion reads."""

    wikichess_dir: str
    openings_dir: str
    milvus_collection: str = "chess_knowledge"


@pytest.fixture
def doubles(monkeypatch: pytest.MonkeyPatch) -> tuple[FakeEmbedder, FakeStore]:
    embedder, store = FakeEmbedder(), FakeStore()
    monkeypatch.setattr(ingest_module, "EmbeddingService", lambda settings: embedder)
    monkeypatch.setattr(ingest_module, "MilvusStore", lambda settings: store)
    return embedder, store


@pytest.fixture
def corpus(tmp_path: Path) -> FakeSettings:
    """Two folders, one article each, as the knowledge base is actually shaped."""
    downloaded, written = tmp_path / "wikichess", tmp_path / "openings"
    downloaded.mkdir()
    written.mkdir()
    (downloaded / "00001-ruy-lopez.md").write_text(ARTICLE, encoding="utf-8")
    (written / "espagnole.md").write_text(ARTICLE, encoding="utf-8")
    return FakeSettings(wikichess_dir=str(downloaded), openings_dir=str(written))


def test_the_two_folders_are_indexed_in_that_order(corpus: FakeSettings) -> None:
    """Downloaded first, hand-written second: a chunk identifier carries its folder."""
    assert [path.name for path in knowledge_directories(corpus)] == ["wikichess", "openings"]


def test_a_passage_can_be_traced_back_to_the_folder_it_came_from(
    corpus: FakeSettings, doubles: tuple[FakeEmbedder, FakeStore]
) -> None:
    """Both corpora land in one collection, so the folder has to travel with the text."""
    _, store = doubles

    ingest(settings=corpus)

    folders = {row[0].split("/")[0] for row in store.rows}
    assert folders == {"wikichess", "openings"}


def test_each_vector_is_inserted_beside_the_text_it_was_computed_from(
    corpus: FakeSettings, doubles: tuple[FakeEmbedder, FakeStore]
) -> None:
    """The silent RAG failure: a passage retrieved under another passage's neighbourhood.

    The fake embedder writes the length of the text into the vector, so a row whose vector
    does not match its own text is visible here and nowhere else.
    """
    embedder, store = doubles

    count = ingest(settings=corpus)

    assert count == len(store.rows)
    assert embedder.seen == [[row[1] for row in store.rows]]
    for _, text, vector in store.rows:
        assert vector == [float(len(text)), 0.0]


def test_the_collection_is_rebuilt_by_default(
    corpus: FakeSettings, doubles: tuple[FakeEmbedder, FakeStore]
) -> None:
    """Re-running the ingestion twice must not double every passage."""
    _, store = doubles

    ingest(settings=corpus)

    assert store.recreated == [True]


def test_an_empty_knowledge_base_stops_before_it_creates_a_collection(
    tmp_path: Path, doubles: tuple[FakeEmbedder, FakeStore]
) -> None:
    """An index with nothing in it answers every question with nothing, and looks healthy."""
    empty = FakeSettings(wikichess_dir=str(tmp_path / "a"), openings_dir=str(tmp_path / "b"))
    _, store = doubles

    with pytest.raises(FileNotFoundError):
        ingest(settings=empty)

    assert store.recreated == []


def test_a_corpus_reduced_to_its_manifest_names_the_command_that_restores_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, doubles: tuple[FakeEmbedder, FakeStore]
) -> None:
    """The articles are not redistributed, so an ordinary clone has the manifest and no text."""
    manifest = tmp_path / "wikichess_manifest.json"
    manifest.write_text(json.dumps({"articles": [{"slug": "a"}, {"slug": "b"}]}), encoding="utf-8")
    monkeypatch.setattr(ingest_module, "WIKICHESS_MANIFEST", manifest)
    downloaded, written = tmp_path / "wikichess", tmp_path / "openings"
    downloaded.mkdir()
    written.mkdir()
    (written / "espagnole.md").write_text(ARTICLE, encoding="utf-8")

    with pytest.raises(FileNotFoundError) as refusal:
        ingest(settings=FakeSettings(wikichess_dir=str(downloaded), openings_dir=str(written)))

    assert "scripts.fetch_wikichess" in str(refusal.value)
    assert "2 articles" in str(refusal.value)


def test_loading_reports_what_each_folder_held(corpus: FakeSettings, capsys) -> None:
    """The ingestion prints its counts: a folder that held nothing is visible in the log."""
    articles = load_knowledge_base(knowledge_directories(corpus))

    assert len(articles) == 2
    assert "wikichess: 1 articles" in capsys.readouterr().out
