"""Vector-search route (Milvus RAG over the Wikichess knowledge base)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from chess_coach.api.dependencies import get_rag_service
from chess_coach.api.schemas import Passage, VectorSearchResponse
from chess_coach.services.milvus_store import MilvusStoreError
from chess_coach.services.rag_search import RagService

router = APIRouter(tags=["rag"])


@router.get("/vector-search", response_model=VectorSearchResponse, summary="Knowledge search")
def vector_search(
    rag: Annotated[RagService, Depends(get_rag_service)],
    q: Annotated[str, Query(min_length=2, description="Natural-language query.")],
    top_k: Annotated[int, Query(ge=1, le=10)] = 3,
) -> VectorSearchResponse:
    """Return the knowledge-base passages most relevant to ``q``."""

    try:
        hits = rag.search(q, top_k=top_k)
    except MilvusStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return VectorSearchResponse(
        query=q,
        passages=[
            Passage(text=hit.text, opening=hit.opening, source=hit.source, score=hit.score)
            for hit in hits
        ],
    )
