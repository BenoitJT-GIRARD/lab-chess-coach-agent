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


class ReferenceGame(BaseModel):
    """A master game reaching the position, as listed by Lichess."""

    game_id: str
    white: str
    black: str
    white_rating: int
    black_rating: int
    winner: str = Field(description='"white", "black" or "draw".')
    year: int | None = None
    url: str = Field(description="Link to the game on Lichess.")
    result: str = Field(description='Result written as "1-0", "0-1" or "1/2-1/2".')


class MovesResponse(BaseModel):
    """Returned by ``GET /api/v1/moves/{fen}``."""

    fen: str
    opening_name: str | None = None
    opening_eco: str | None = None
    total_games: int = 0
    in_theory: bool = Field(description="Whether the position is known to theory.")
    moves: list[MoveStat] = Field(default_factory=list)
    reference_games: list[ReferenceGame] = Field(default_factory=list)


class Passage(BaseModel):
    """A knowledge-base passage retrieved by vector search."""

    text: str
    opening: str
    source: str
    score: float = Field(description="Similarity score (higher is closer).")


class VectorSearchResponse(BaseModel):
    """Returned by ``GET /api/v1/vector-search``."""

    query: str
    passages: list[Passage] = Field(default_factory=list)


class VideoResult(BaseModel):
    """A single YouTube video suggestion."""

    video_id: str
    title: str
    channel: str
    url: str
    thumbnail: str


class VideosResponse(BaseModel):
    """Returned by ``GET /api/v1/videos/{opening}``."""

    opening: str
    videos: list[VideoResult] = Field(default_factory=list)


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


class AgentRequest(BaseModel):
    """Body of ``POST /api/v1/agent``."""

    fen: str = Field(description="Position to analyse, in FEN notation.")


class AgentResponse(BaseModel):
    """Full agent answer for a position."""

    fen: str
    valid: bool
    opening_name: str | None = None
    opening_eco: str | None = None
    in_theory: bool = False
    theory_moves: list[MoveStat] = Field(default_factory=list)
    reference_games: list[ReferenceGame] = Field(default_factory=list)
    evaluation: EvaluationResponse | None = None
    passages: list[Passage] = Field(default_factory=list)
    videos: list[VideoResult] = Field(default_factory=list)
    recommendation: str = ""
    sources_used: list[str] = Field(default_factory=list)
    error: str | None = None
