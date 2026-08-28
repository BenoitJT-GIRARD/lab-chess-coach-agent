"""Load the Wikichess knowledge base into Milvus.

Usage (from the repository root or inside the backend container)::

    python -m scripts.ingest_wikichess
"""

from __future__ import annotations

from chess_coach.config import get_settings
from chess_coach.rag.ingest import ingest


def main() -> None:
    settings = get_settings()
    print(f"Embedding model : {settings.embedding_model}")
    print(f"Milvus          : {settings.milvus_host}:{settings.milvus_port}")
    print(f"Articles        : {settings.wikichess_dir}")

    count = ingest()
    print(f"Indexed {count} chunks into collection '{settings.milvus_collection}'.")


if __name__ == "__main__":
    main()
