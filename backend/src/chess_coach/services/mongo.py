"""MongoDB persistence service.

Every agent interaction — the position looked at and the recommendation
produced — is stored in MongoDB. A coach can then see what the young players
actually work on, and the demonstration can show the history growing.

Persistence is best-effort: a database outage logs a warning but never breaks
the agent's answer. The player came for advice, not for a stack trace.
"""

from __future__ import annotations

import logging
from typing import Any

from chess_coach.config import Settings, get_settings

logger = logging.getLogger(__name__)


class MongoService:
    """Store and read back the agent's interactions."""

    _COLLECTION = "interactions"

    def __init__(self, settings: Settings | None = None, client: Any | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = client

    def _get_client(self) -> Any:
        """Connect to MongoDB on first use (short timeout, cached)."""

        if self._client is None:
            from pymongo import MongoClient

            self._client = MongoClient(
                self._settings.mongodb_uri,
                serverSelectionTimeoutMS=2000,
            )
        return self._client

    def _collection(self) -> Any:
        return self._get_client()[self._settings.mongodb_db][self._COLLECTION]

    def save_interaction(self, document: dict) -> str | None:
        """Persist one interaction; return its id, or ``None`` on failure."""

        try:
            result = self._collection().insert_one(dict(document))
            return str(result.inserted_id)
        except Exception as exc:
            logger.warning("Could not persist interaction to MongoDB: %s", exc)
            return None

    def count_interactions(self) -> int:
        """Return the number of stored interactions (0 if unreachable)."""

        try:
            return int(self._collection().count_documents({}))
        except Exception as exc:
            logger.warning("Could not count interactions in MongoDB: %s", exc)
            return 0

    def recent_interactions(self, limit: int = 10) -> list[dict]:
        """Return the most recent interactions, newest first.

        The Mongo document id is dropped: it is an internal detail, and it does
        not serialise to JSON.
        """

        try:
            documents = (
                self._collection().find({}, {"_id": False}).sort("created_at", -1).limit(limit)
            )
            return list(documents)
        except Exception as exc:
            logger.warning("Could not read the interactions from MongoDB: %s", exc)
            return []
