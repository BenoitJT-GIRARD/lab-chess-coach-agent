"""Pydantic response models exposed by the API.

Keeping the response schemas in one place documents the public contract of the
service and lets FastAPI generate an accurate OpenAPI / Swagger description.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Returned by ``GET /api/v1/healthcheck``."""

    status: Literal["ok"] = "ok"
    service: str = Field(description="Name of the running service.")
    version: str = Field(description="Deployed package version.")


class PositionResponse(BaseModel):
    """Structured description of a chess position (``GET /api/v1/position``)."""

    fen: str
    side_to_move: str = Field(description='"white" or "black".')
    fullmove_number: int
    castling_rights: str
    is_check: bool
    is_game_over: bool
    legal_moves_san: list[str] = Field(description="Legal moves in SAN notation.")
    board_ascii: str = Field(description="ASCII diagram of the board.")


class MoveStat(BaseModel):
    """A theoretical move and its aggregated game statistics."""

    uci: str
    san: str
    white: int = Field(description="Games won by White.")
    draws: int
    black: int = Field(description="Games won by Black.")
    total: int = Field(description="Total games where the move was played.")
    source: str = Field(default="lichess", description='Origin of the move: "lichess" or "book".')


class MovesResponse(BaseModel):
    """Returned by ``GET /api/v1/moves/{fen}``."""

    fen: str
    opening_name: str | None = None
    opening_eco: str | None = None
    total_games: int = 0
    in_theory: bool = Field(description="Whether the position is known to theory.")
    moves: list[MoveStat] = Field(default_factory=list)


class EvaluationResponse(BaseModel):
    """Returned by ``GET /api/v1/evaluate/{fen}``."""

    fen: str
    evaluation_type: Literal["cp", "mate"] = Field(
        description='"cp" for centipawns, "mate" for a forced mate distance.'
    )
    value: int = Field(description="Score from White's perspective.")
    perspective: Literal["white"] = "white"
    best_move: str | None = None
    best_move_san: str | None = None
    depth: int
