"""Milvus vector store.

Encapsulates every interaction with the Milvus vector database: creating the
collection and its index, inserting embedded chunks, and running similarity
searches. The rest of the code never imports pymilvus directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from chess_coach.config import Settings, get_settings
from chess_coach.rag.preprocess import Chunk


class MilvusStoreError(RuntimeError):
    """Raised when the Milvus vector store cannot be reached or queried."""


@dataclass(slots=True)
class SearchHit:
    """A single search result from the vector store."""

    text: str
    opening: str
    source: str
    score: float


class MilvusStore:
    """Thin wrapper around a Milvus collection of opening-knowledge chunks."""

    _TEXT_MAX_LENGTH = 8192

    def __init__(self, settings: Settings | None = None, client: Any | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = client
        self._name = self._settings.milvus_collection

    @property
    def uri(self) -> str:
        """Milvus connection URI built from the configured host and port."""

        return f"http://{self._settings.milvus_host}:{self._settings.milvus_port}"

    def _get_client(self) -> Any:
        """Connect to Milvus on first use (lazy, cached)."""

        if self._client is None:
            try:
                from pymilvus import MilvusClient

                self._client = MilvusClient(uri=self.uri, timeout=self._settings.milvus_timeout)
            except Exception as exc:  # pragma: no cover - needs a live server
                raise MilvusStoreError(f"Could not connect to Milvus at {self.uri}") from exc
        return self._client

    def ensure_collection(self, *, recreate: bool = False) -> None:
        """Create the collection and its vector index if they do not exist."""

        from pymilvus import DataType

        client = self._get_client()
        if recreate and client.has_collection(self._name):
            client.drop_collection(self._name)
        if client.has_collection(self._name):
            return

        schema = client.create_schema(auto_id=False, enable_dynamic_field=False)
        schema.add_field("id", DataType.VARCHAR, is_primary=True, max_length=128)
        schema.add_field("embedding", DataType.FLOAT_VECTOR, dim=self._settings.embedding_dim)
        schema.add_field("text", DataType.VARCHAR, max_length=self._TEXT_MAX_LENGTH)
        schema.add_field("opening", DataType.VARCHAR, max_length=256)
        schema.add_field("source", DataType.VARCHAR, max_length=256)

        index_params = client.prepare_index_params()
        index_params.add_index(field_name="embedding", index_type="AUTOINDEX", metric_type="IP")

        client.create_collection(self._name, schema=schema, index_params=index_params)

    def insert(self, chunks: list[Chunk], embeddings: list[list[float]]) -> int:
        """Insert chunks and their embeddings; returns the number of rows."""

        client = self._get_client()
        rows = [
            {
                "id": chunk.chunk_id,
                "embedding": embedding,
                "text": chunk.text[: self._TEXT_MAX_LENGTH],
                "opening": chunk.opening,
                "source": chunk.source,
            }
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]
        client.insert(collection_name=self._name, data=rows)
        return len(rows)

    def search(self, query_embedding: list[float], *, top_k: int = 3) -> list[SearchHit]:
        """Return the ``top_k`` most similar chunks to ``query_embedding``."""

        client = self._get_client()
        try:
            results = client.search(
                collection_name=self._name,
                data=[query_embedding],
                limit=top_k,
                output_fields=["text", "opening", "source"],
                search_params={"metric_type": "IP"},
                timeout=self._settings.milvus_timeout,
            )
        except Exception as exc:  # pragma: no cover - needs a live server
            raise MilvusStoreError("Milvus search failed") from exc

        hits: list[SearchHit] = []
        for hit in results[0]:
            entity = hit.get("entity", {})
            hits.append(
                SearchHit(
                    text=entity.get("text", ""),
                    opening=entity.get("opening", ""),
                    source=entity.get("source", ""),
                    score=float(hit.get("distance", 0.0)),
                )
            )
        return hits
