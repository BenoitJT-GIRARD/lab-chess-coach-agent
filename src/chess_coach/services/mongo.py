"""MongoDB persistence service.

Every agent interaction (the position queried and the recommendation produced)
is stored in MongoDB so a coach could later analyse usage, cache answers or
build a training history. Persistence is best-effort: a database outage logs a
warning but never breaks the agent's answer.
"""

from __future__ import annotations

import logging
from typing import Any

from chess_coach.config import Settings, get_settings

logger = logging.getLogger(__name__)


class MongoService:
    """Store and count agent interactions in MongoDB."""

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
        except Exception as exc:  # pragma: no cover - needs a live server
            logger.warning("Could not persist interaction to MongoDB: %s", exc)
            return None

    def count_interactions(self) -> int:
        """Return the number of stored interactions (0 if unreachable)."""

        try:
            return int(self._collection().count_documents({}))
        except Exception as exc:  # pragma: no cover - needs a live server
            logger.warning("Could not count interactions in MongoDB: %s", exc)
            return 0
