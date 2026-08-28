"""Chess Coach — a LangGraph chess-opening coaching agent.

The package is organised in clearly separated layers so that the reasoning
behind the project stays readable:

- :mod:`chess_coach.config`   — centralised settings (environment variables).
- :mod:`chess_coach.services` — business logic talking to external systems
  (Lichess, Stockfish, YouTube, Milvus, MongoDB).
- :mod:`chess_coach.rag`      — Wikichess knowledge base preprocessing and ingestion.
- :mod:`chess_coach.agent`    — the LangGraph orchestration graph.
- :mod:`chess_coach.api`      — the thin FastAPI layer exposing the agent.
"""

from __future__ import annotations

__version__ = "0.1.0"
