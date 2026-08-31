"""History route: what the agent has already been asked.

Every run of the agent is written to MongoDB by the last node of the graph.
This route reads that collection back, which is what makes the database
visible during the demonstration.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from chess_coach.api.dependencies import get_mongo_service
from chess_coach.api.schemas import HistoryResponse, Interaction
from chess_coach.services.mongo import MongoService

router = APIRouter(tags=["history"])


@router.get("/history", response_model=HistoryResponse, summary="Recent interactions")
def get_history(
    mongo: Annotated[MongoService, Depends(get_mongo_service)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> HistoryResponse:
    """Return the positions the agent analysed most recently."""

    documents = mongo.recent_interactions(limit=limit)
    return HistoryResponse(
        total=mongo.count_interactions(),
        interactions=[
            Interaction(
                fen=document.get("fen", ""),
                opening_name=document.get("opening_name"),
                in_theory=bool(document.get("in_theory")),
                sources_used=document.get("sources_used", []),
                created_at=document.get("created_at", ""),
            )
            for document in documents
        ],
    )
