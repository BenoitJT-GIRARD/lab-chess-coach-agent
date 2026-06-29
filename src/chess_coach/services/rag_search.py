"""Retrieval service: turn a natural-language query into relevant passages.

This is the read side of the RAG pipeline used by both the ``/vector-search``
endpoint and the LangGraph agent: embed the query, search Milvus, return the
best passages.
"""

from __future__ import annotations

from chess_coach.config import Settings, get_settings
from chess_coach.services.embeddings import EmbeddingService
from chess_coach.services.milvus_store import MilvusStore, SearchHit


class RagService:
    """Embed a query and retrieve the most relevant opening passages."""

    def __init__(
        self,
        settings: Settings | None = None,
        embedder: EmbeddingService | None = None,
        store: MilvusStore | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._embedder = embedder or EmbeddingService(self._settings)
        self._store = store or MilvusStore(self._settings)

    def search(self, query: str, *, top_k: int = 3) -> list[SearchHit]:
        """Return the ``top_k`` passages most relevant to ``query``."""

        query_embedding = self._embedder.embed_one(query)
        return self._store.search(query_embedding, top_k=top_k)
