"""Sentence embedding service.

Wraps a sentence-transformers model so the rest of the code depends on a small,
stable interface (``embed`` / ``embed_one``) rather than on the library. The
model is loaded lazily — and only once — because loading it is the expensive
part. Embeddings are L2-normalised so that an inner-product search in Milvus is
equivalent to cosine similarity.
"""

from __future__ import annotations

from typing import Any

from chess_coach.config import Settings, get_settings


class EmbeddingService:
    """Encode text into dense vectors with a sentence-transformers model."""

    def __init__(self, settings: Settings | None = None, model: Any | None = None) -> None:
        self._settings = settings or get_settings()
        self._model = model

    def _get_model(self) -> Any:
        """Load the embedding model on first use and cache it."""

        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._settings.embedding_model)
        return self._model

    @property
    def dim(self) -> int:
        """Configured embedding dimension."""

        return self._settings.embedding_dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts into normalised vectors."""

        model = self._get_model()
        vectors = model.encode(texts, normalize_embeddings=True)
        return [vector.tolist() for vector in vectors]

    def embed_one(self, text: str) -> list[float]:
        """Embed a single text into a normalised vector."""

        return self.embed([text])[0]
