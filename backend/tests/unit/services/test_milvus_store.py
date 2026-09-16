"""The vector store, driven through a fake client.

`MilvusStore` is the only module that speaks to pymilvus, and it takes a client in its
constructor precisely so this tier can hand it one. What is tested is the part written here:
the address it builds, what it puts in a row, what it does before recreating a collection,
and how a raw hit becomes a `SearchHit`. The database's own behaviour is not under test and
could not be.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from chess_coach.rag.preprocess import Chunk
from chess_coach.services.milvus_store import MilvusStore


@dataclass
class FakeSettings:
    milvus_host: str = "milvus"
    milvus_port: int = 19530
    milvus_collection: str = "chess_knowledge"
    embedding_dim: int = 384
    milvus_timeout: float = 3.0


@dataclass
class FakeClient:
    """Records the calls, and answers `has_collection` from a flag the test sets."""

    exists: bool = False
    dropped: list[str] = field(default_factory=list)
    created: list[str] = field(default_factory=list)
    inserted: list[dict[str, Any]] = field(default_factory=list)
    hits: list[dict[str, Any]] = field(default_factory=list)
    searched: list[dict[str, Any]] = field(default_factory=list)

    def has_collection(self, name: str) -> bool:
        return self.exists

    def drop_collection(self, name: str) -> None:
        self.dropped.append(name)
        self.exists = False

    def create_schema(self, **_: Any) -> FakeSchema:
        return FakeSchema()

    def prepare_index_params(self) -> FakeIndexParams:
        return FakeIndexParams()

    def create_collection(self, collection_name: str, **_: Any) -> None:
        self.created.append(collection_name)
        self.exists = True

    def insert(self, collection_name: str, data: list[dict[str, Any]]) -> None:
        self.inserted = data

    def search(self, **kwargs: Any) -> list[list[dict[str, Any]]]:
        self.searched.append(kwargs)
        return [self.hits]


class FakeSchema:
    def add_field(self, *args: Any, **kwargs: Any) -> None:
        return None


class FakeIndexParams:
    def add_index(self, **kwargs: Any) -> None:
        return None


def chunk(text: str, chunk_id: str = "wikichess/ruy-lopez-0") -> Chunk:
    return Chunk(chunk_id=chunk_id, opening="Ruy Lopez", source="wikichess/ruy-lopez.md", text=text)


def test_the_address_is_built_from_the_configured_host_and_port() -> None:
    """Inside the compose network the host is a service name, not localhost."""
    store = MilvusStore(FakeSettings(), client=FakeClient())

    assert store.uri == "http://milvus:19530"


def test_a_row_carries_the_passage_its_vector_was_computed_from() -> None:
    client = FakeClient()
    store = MilvusStore(FakeSettings(), client=client)

    written = store.insert([chunk("the Spanish game")], [[0.1, 0.2]])

    assert written == 1
    assert client.inserted[0]["text"] == "the Spanish game"
    assert client.inserted[0]["embedding"] == [0.1, 0.2]
    assert client.inserted[0]["source"] == "wikichess/ruy-lopez.md"


def test_a_passage_longer_than_the_field_is_cut_rather_than_refused() -> None:
    """The schema declares 8192 characters. A longer chunk would be rejected by the server.

    Cutting is a decision, not an accident: the chunker aims at 600 characters, so a passage
    that reaches this length is a malformed article rather than a long paragraph, and losing
    its tail is better than losing the whole ingestion.
    """
    client = FakeClient()
    store = MilvusStore(FakeSettings(), client=client)

    store.insert([chunk("x" * 9000)], [[0.0, 0.0]])

    assert len(client.inserted[0]["text"]) == 8192


def test_recreating_drops_the_collection_before_building_it() -> None:
    """Re-running the ingestion without this leaves every passage in the index twice."""
    client = FakeClient(exists=True)
    store = MilvusStore(FakeSettings(), client=client)

    store.ensure_collection(recreate=True)

    assert client.dropped == ["chess_knowledge"]
    assert client.created == ["chess_knowledge"]


def test_an_existing_collection_is_left_alone_when_recreation_is_not_asked_for() -> None:
    client = FakeClient(exists=True)
    store = MilvusStore(FakeSettings(), client=client)

    store.ensure_collection()

    assert client.dropped == []
    assert client.created == []


def test_a_hit_becomes_a_passage_with_its_similarity() -> None:
    """`distance` is what Milvus calls it and `score` is what the API publishes."""
    client = FakeClient(
        hits=[
            {
                "distance": 0.83,
                "entity": {
                    "text": "Black answers 3...a6",
                    "opening": "Ruy Lopez",
                    "source": "wikichess/ruy-lopez.md",
                },
            }
        ]
    )
    store = MilvusStore(FakeSettings(), client=client)

    found = store.search([0.1, 0.2], top_k=1)

    assert found[0].score == 0.83
    assert found[0].opening == "Ruy Lopez"


def test_a_hit_with_no_stored_text_reads_as_empty_rather_than_crashing() -> None:
    """An index built by an older schema answers with fields this code does not know."""
    store = MilvusStore(FakeSettings(), client=FakeClient(hits=[{"distance": 0.4}]))

    found = store.search([0.1, 0.2])

    assert found[0].text == ""
    assert found[0].score == 0.4


def test_a_search_carries_a_deadline() -> None:
    """Without one, pymilvus retries a closed port for about ten seconds.

    The route answers 503 either way. What changes is whether it answers while someone is
    still looking at the page, and the system tier found it the long way round: a request
    that had not come back after thirty seconds.
    """
    client = FakeClient(hits=[])
    store = MilvusStore(FakeSettings(), client=client)

    store.search([0.1, 0.2])

    assert client.searched[0]["timeout"] == 3.0
