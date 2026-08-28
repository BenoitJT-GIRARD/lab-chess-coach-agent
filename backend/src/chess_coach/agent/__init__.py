"""LangGraph agent orchestrating the chess-opening coaching tools.

The agent is a small decision graph: it identifies the position, looks up
theory, decides whether to call the engine, enriches the answer with retrieved
knowledge and videos, writes a recommendation and persists the interaction.
"""

from __future__ import annotations
