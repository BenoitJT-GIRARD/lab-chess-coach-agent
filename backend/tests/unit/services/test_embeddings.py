"""The embedding service, with the model replaced.

One line of this module decides whether the whole retrieval means anything:
``model.encode(texts, normalize_embeddings=True)``. Milvus is configured for inner product,
and inner product equals cosine similarity only on unit vectors. Drop the flag and the search
still runs, still returns passages, and starts ranking long chunks above relevant ones —
silently, and with a score that still looks like a similarity.

The fake model records what it was asked, which is the only way to say that from here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from chess_coach.services.embeddings import EmbeddingService


@dataclass
class FakeSettings:
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384


@dataclass
class FakeModel:
    """Returns numpy rows, the way sentence-transformers does."""

    calls: list[dict[str, Any]] = field(default_factory=list)

    def encode(self, texts: list[str], **kwargs: Any) -> Any:
        self.calls.append({"texts": list(texts), **kwargs})
        return np.array([[float(len(text)), 1.0, 0.0] for text in texts], dtype=np.float32)


def test_the_vectors_are_asked_for_normalised() -> None:
    """Inner product in Milvus is cosine similarity only if the vectors are unit length."""
    model = FakeModel()

    EmbeddingService(FakeSettings(), model=model).embed(["the Ruy Lopez"])

    assert model.calls[0]["normalize_embeddings"] is True


def test_a_batch_is_embedded_in_one_call_and_in_order() -> None:
    """One call per batch, not one per passage: the corpus is a few thousand chunks."""
    model = FakeModel()

    vectors = EmbeddingService(FakeSettings(), model=model).embed(["a", "bbb", "cc"])

    assert len(model.calls) == 1
    assert [vector[0] for vector in vectors] == [1.0, 3.0, 2.0]


def test_what_leaves_the_service_is_a_list_and_not_a_numpy_row() -> None:
    """The vectors go to pymilvus and to JSON, neither of which takes a numpy array."""
    vectors = EmbeddingService(FakeSettings(), model=FakeModel()).embed(["a"])

    assert isinstance(vectors, list)
    assert isinstance(vectors[0], list)
    assert all(isinstance(value, float) for value in vectors[0])


def test_a_single_text_comes_back_as_one_vector_rather_than_a_batch_of_one() -> None:
    """The search path embeds one query, and hands it straight to `MilvusStore.search`."""
    vector = EmbeddingService(FakeSettings(), model=FakeModel()).embed_one("the Ruy Lopez")

    assert vector == [13.0, 1.0, 0.0]


def test_the_configured_dimension_is_the_one_the_collection_is_built_with() -> None:
    """`MilvusStore.ensure_collection` declares this number; a mismatch is a refused insert."""
    assert EmbeddingService(FakeSettings(), model=FakeModel()).dim == 384
