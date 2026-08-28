"""Load the opening knowledge base into Milvus.

Usage (from the ``backend/`` folder or inside the backend container)::

    python -m scripts.ingest_wikichess

The articles themselves are downloaded once by ``scripts.fetch_wikichess`` and
committed with the project, so this step never needs the network.
"""

from __future__ import annotations

from chess_coach.config import get_settings
from chess_coach.rag.ingest import ingest, knowledge_directories


def main() -> None:
    settings = get_settings()
    print(f"Embedding model : {settings.embedding_model}")
    print(f"Milvus          : {settings.milvus_host}:{settings.milvus_port}")
    print("Base de connaissances :")
    for directory in knowledge_directories(settings):
        print(f"  - {directory}")

    count = ingest()
    print(f"\n{count} chunks indexés dans la collection '{settings.milvus_collection}'.")


if __name__ == "__main__":
    main()
