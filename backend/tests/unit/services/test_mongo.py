"""History persistence, and the promise that it never costs an answer.

The module promises that an outage costs a log line and nothing else. That promise is the
behaviour worth testing, and the one a reader cannot check by looking: every call sits inside
a try block, and a block that swallows the wrong exception looks exactly like one that
swallows the right one.

The fake below fails the way a real outage fails: at the moment of the call, not at
construction.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from chess_coach.services.mongo import MongoService


@dataclass
class FakeSettings:
    mongodb_uri: str = "mongodb://mongo:27017"
    mongodb_db: str = "chess_coach"


@dataclass
class FakeCollection:
    documents: list[dict] = field(default_factory=list)

    def insert_one(self, document: dict) -> Any:
        # pymongo writes the generated `_id` back into the dictionary it was given. The fake
        # does the same, because that is what the service copies the document to avoid.
        document["_id"] = f"id-{len(self.documents) + 1}"
        self.documents.append(document)
        return type("Inserted", (), {"inserted_id": document["_id"]})()

    def count_documents(self, _filter: dict) -> int:
        return len(self.documents)

    def find(self, _filter: dict, projection: dict) -> FakeCursor:
        return FakeCursor([dict(d) for d in self.documents], projection)


@dataclass
class FakeCursor:
    documents: list[dict]
    projection: dict

    def sort(self, key: str, direction: int) -> FakeCursor:
        self.documents.sort(key=lambda d: d.get(key, ""), reverse=direction < 0)
        return self

    def limit(self, count: int) -> list[dict]:
        kept = self.documents[:count]
        if self.projection.get("_id") is False:
            kept = [{k: v for k, v in d.items() if k != "_id"} for d in kept]
        return kept


class FakeClient:
    """`client[database][collection]`, the way pymongo is indexed."""

    def __init__(self, collection: FakeCollection) -> None:
        self._collection = collection

    def __getitem__(self, _name: str) -> Any:
        return _Database(self._collection)


@dataclass
class _Database:
    collection: FakeCollection

    def __getitem__(self, _name: str) -> FakeCollection:
        return self.collection


class UnreachableClient:
    """Every access raises, as a closed port does once the driver gives up waiting."""

    def __getitem__(self, _name: str) -> Any:
        raise ConnectionError("No replica set members available")


def service(collection: FakeCollection | None = None) -> MongoService:
    return MongoService(FakeSettings(), client=FakeClient(collection or FakeCollection()))


def test_an_interaction_is_stored_and_its_identifier_returned() -> None:
    collection = FakeCollection()

    identifier = service(collection).save_interaction({"fen": "8/8/8/8/8/8/8/K6k w - - 0 1"})

    assert identifier == "id-1"
    assert collection.documents[0]["fen"].startswith("8/8")


def test_the_caller_does_not_get_a_mongo_identifier_written_into_its_own_state() -> None:
    """pymongo writes `_id` back into the dictionary it is handed. Here that dictionary is the
    agent's answer, on its way to the API, and an ObjectId does not serialise to JSON.

    The service copies before inserting. This is the test of that copy, and the reason it
    exists: without it the history route answers 500 on the first save.
    """
    collection = FakeCollection()
    document = {"fen": "8/8/8/8/8/8/8/K6k w - - 0 1", "sources_used": ["lichess"]}

    identifier = service(collection).save_interaction(document)

    assert identifier == "id-1"
    assert "_id" not in document
    assert "_id" in collection.documents[0]


def test_the_history_is_returned_newest_first_and_without_the_internal_id() -> None:
    """`_id` is an ObjectId: it is not JSON, and the route publishes this list as it is."""
    collection = FakeCollection(
        documents=[
            {"_id": 1, "fen": "a", "created_at": "2026-09-01T10:00:00"},
            {"_id": 2, "fen": "b", "created_at": "2026-09-03T10:00:00"},
        ]
    )

    history = service(collection).recent_interactions()

    assert [d["fen"] for d in history] == ["b", "a"]
    assert "_id" not in history[0]


def test_the_limit_is_honoured() -> None:
    collection = FakeCollection(
        documents=[{"fen": str(i), "created_at": str(i)} for i in range(30)]
    )

    assert len(service(collection).recent_interactions(limit=5)) == 5


def test_a_database_that_is_not_there_costs_the_player_nothing(
    caplog: logging.LogCaptureFixture,
) -> None:
    """The three calls degrade to None, 0 and an empty list, and each says so in the log."""
    unreachable = MongoService(FakeSettings(), client=UnreachableClient())

    with caplog.at_level(logging.WARNING):
        saved = unreachable.save_interaction({"fen": "8/8/8/8/8/8/8/K6k w - - 0 1"})
        counted = unreachable.count_interactions()
        listed = unreachable.recent_interactions()

    assert (saved, counted, listed) == (None, 0, [])
    assert len(caplog.records) == 3
    assert all("MongoDB" in record.message for record in caplog.records)
