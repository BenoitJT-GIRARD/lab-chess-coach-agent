"""Centralised application settings.

Every tunable value (hosts, ports, API keys, model names) is read from the
environment — never hard-coded — so the same code runs identically on a
developer laptop and inside Docker Compose. Values are documented in
``.env.example``.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration sourced from environment variables / ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- API ---
    # Binding to all interfaces is intentional: the API only ever runs inside a
    # container whose published ports are controlled by docker-compose.
    api_host: str = "0.0.0.0"  # nosec B104
    api_port: int = 8000

    # --- Lichess ---
    lichess_explorer_base: str = "https://explorer.lichess.ovh"
    lichess_api_base: str = "https://lichess.org"
    # The Opening Explorer requires an authenticated request. A personal token
    # with no scope is enough; when it is missing the agent falls back to the
    # local opening book (see services/opening_book.py).
    lichess_token: str = ""
    # "masters" holds over-the-board master games — the reference games the
    # brief asks for. "lichess" would hold every rated game played on the site.
    lichess_database: str = "masters"
    # Number of reference games shown alongside the theoretical moves.
    lichess_reference_games: int = 3
    # Below this number of master games, a position is treated as out of
    # theory. The master database answers for almost any legal position, so a
    # threshold is what separates a studied line from a curiosity: the Italian
    # Game is backed by about 49 000 games, 1.e4 e5 2.Qh5 by 48.
    theory_min_games: int = 1000

    # --- Stockfish ---
    stockfish_path: str = "/usr/games/stockfish"
    stockfish_depth: int = 15
    stockfish_threads: int = 1

    # --- YouTube Data API v3 ---
    youtube_api_key: str = ""

    # --- Milvus ---
    milvus_host: str = "milvus"
    milvus_port: int = 19530
    milvus_collection: str = "chess_openings"

    # The knowledge base is made of two folders of Markdown articles, both
    # relative to the working directory.
    #   - wikichess: articles downloaded from FICGS Wikichess (the source the
    #     brief points to), in English;
    #   - openings: complementary notes written in French for young players.
    wikichess_dir: str = "data/wikichess"
    openings_dir: str = "data/openings"

    # --- Embeddings ---
    # Multilingual model: the Wikichess knowledge base is in French. 384-dim,
    # lightweight and CPU-friendly, in the spirit of the brief's suggestion.
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dim: int = 384

    # --- MongoDB ---
    mongodb_uri: str = "mongodb://mongo:27017"
    mongodb_db: str = "chess_coach"

    # --- Optional LLM synthesis layer ---
    llm_enabled: bool = False
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    # External HTTP timeout (seconds) shared by every service client.
    http_timeout: float = Field(default=10.0, ge=1.0)


@lru_cache
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance.

    Caching guarantees the environment is parsed once and that every module
    sees the same configuration object.
    """

    return Settings()
