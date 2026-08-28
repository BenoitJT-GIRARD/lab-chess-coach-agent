"""Business-logic services.

Each module in this package encapsulates the interaction with one external
system (Lichess, Stockfish, YouTube, Milvus, MongoDB) or one self-contained
domain concern (chess position handling). The API and the agent depend on these
services, never the other way around — this keeps the business logic decoupled
from the transport layer.
"""

from __future__ import annotations
