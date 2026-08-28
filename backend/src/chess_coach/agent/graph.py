"""The LangGraph chess-opening coaching agent.

Graph shape::

    START -> identify -> (valid?) -> theory -> (in theory?) -> context -> videos
                              |                      |                       |
                              v                      v                       v
                             END                  engine ----------------> synthesize -> persist -> END

The agent decides which information source is appropriate: theory from the
opening book / Lichess when the position is known, and the Stockfish engine
when it is not. It then always enriches the answer with retrieved knowledge and
videos before writing a recommendation and persisting the interaction.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime

from langgraph.graph import END, START, StateGraph

from chess_coach.agent.state import AgentDeps, AgentState
from chess_coach.agent.synthesize import build_recommendation
from chess_coach.config import get_settings
from chess_coach.services.chess_position import describe_position, is_valid_fen
from chess_coach.services.lichess import LichessServiceError
from chess_coach.services.milvus_store import MilvusStoreError
from chess_coach.services.mongo import MongoService
from chess_coach.services.rag_search import RagService
from chess_coach.services.stockfish_engine import StockfishService, StockfishServiceError
from chess_coach.services.theory import TheoryService
from chess_coach.services.youtube import YoutubeService, YoutubeServiceError


def build_context_query(state: AgentState) -> str:
    """Build the question asked to the knowledge base.

    Searching on the bare opening name is too vague: several articles mention
    it in passing. Adding what the young player is actually looking for — the
    ideas, the plans, the main moves — pulls the explanatory paragraphs to the
    top instead of the first passage that happens to quote the name.
    """

    opening = state.get("opening_name")
    if not opening:
        return "principes généraux des ouvertures aux échecs"

    eco = state.get("opening_eco")
    label = f"{opening} {eco}" if eco else opening
    return f"{label} chess opening: main ideas, plans and moves"


def build_graph(deps: AgentDeps):
    """Build and compile the agent graph wired to ``deps``."""

    def identify(state: AgentState) -> AgentState:
        fen = state["fen"]
        if not is_valid_fen(fen):
            return {"valid": False, "error": f"Invalid FEN: {fen!r}"}
        return {"valid": True, "position": asdict(describe_position(fen))}

    def lookup_theory(state: AgentState) -> AgentState:
        try:
            result = deps.theory.get_theoretical_moves(state["fen"])
        except LichessServiceError:
            return {
                "in_theory": False,
                "theory_moves": [],
                "reference_games": [],
                "opening_name": None,
            }
        moves = [
            {
                "uci": move.uci,
                "san": move.san,
                "white": move.white,
                "draws": move.draws,
                "black": move.black,
                "total": move.total,
                "source": move.source,
            }
            for move in result.moves
        ]
        games = [
            {
                "game_id": game.game_id,
                "white": game.white,
                "black": game.black,
                "white_rating": game.white_rating,
                "black_rating": game.black_rating,
                "winner": game.winner,
                "year": game.year,
                "url": game.url,
                "result": game.result,
            }
            for game in result.reference_games
        ]
        return {
            "in_theory": result.in_theory,
            "opening_name": result.opening_name,
            "opening_eco": result.opening_eco,
            "theory_moves": moves,
            "reference_games": games,
            "sources_used": ["theory"] if result.in_theory else [],
        }

    def evaluate_engine(state: AgentState) -> AgentState:
        try:
            evaluation = deps.stockfish.evaluate(state["fen"])
        except StockfishServiceError as exc:
            return {"evaluation": None, "error": str(exc)}
        return {"evaluation": asdict(evaluation), "sources_used": ["engine"]}

    def retrieve_context(state: AgentState) -> AgentState:
        query = build_context_query(state)
        try:
            hits = deps.rag.search(query, top_k=3)
        except MilvusStoreError:
            return {"passages": []}
        passages = [asdict(hit) for hit in hits]
        return {"passages": passages, "sources_used": ["rag"] if passages else []}

    def find_videos(state: AgentState) -> AgentState:
        if not deps.youtube.is_configured:
            return {"videos": []}
        query = state.get("opening_name") or "chess opening"
        try:
            videos = deps.youtube.search_videos(query, max_results=4)
        except YoutubeServiceError:
            return {"videos": []}
        items = [asdict(video) for video in videos]
        return {"videos": items, "sources_used": ["youtube"] if items else []}

    def synthesize(state: AgentState) -> AgentState:
        recommendation = build_recommendation(state, deps.settings)
        return {
            "recommendation": recommendation.text,
            "sources_used": ["llm"] if recommendation.used_llm else [],
        }

    def persist(state: AgentState) -> AgentState:
        document = {
            "fen": state.get("fen"),
            "opening_name": state.get("opening_name"),
            "in_theory": state.get("in_theory"),
            "recommendation": state.get("recommendation"),
            "sources_used": state.get("sources_used", []),
            "created_at": datetime.now(UTC).isoformat(),
        }
        deps.mongo.save_interaction(document)
        return {}

    def route_after_identify(state: AgentState) -> str:
        return "theory" if state.get("valid") else "end"

    def route_after_theory(state: AgentState) -> str:
        return "context" if state.get("in_theory") else "engine"

    graph = StateGraph(AgentState)
    graph.add_node("identify", identify)
    graph.add_node("theory", lookup_theory)
    graph.add_node("engine", evaluate_engine)
    graph.add_node("context", retrieve_context)
    graph.add_node("videos", find_videos)
    graph.add_node("synthesize", synthesize)
    graph.add_node("persist", persist)

    graph.add_edge(START, "identify")
    graph.add_conditional_edges("identify", route_after_identify, {"theory": "theory", "end": END})
    graph.add_conditional_edges(
        "theory", route_after_theory, {"context": "context", "engine": "engine"}
    )
    graph.add_edge("engine", "context")
    graph.add_edge("context", "videos")
    graph.add_edge("videos", "synthesize")
    graph.add_edge("synthesize", "persist")
    graph.add_edge("persist", END)

    return graph.compile()


class ChessAgent:
    """High-level wrapper around the compiled LangGraph agent."""

    def __init__(self, deps: AgentDeps) -> None:
        self._deps = deps
        self._graph = build_graph(deps)

    def run(self, fen: str) -> AgentState:
        """Run the agent on a position and return the final state."""

        return self._graph.invoke({"fen": fen, "sources_used": []})


def build_default_agent() -> ChessAgent:
    """Construct a :class:`ChessAgent` wired to the real services."""

    settings = get_settings()
    deps = AgentDeps(
        settings=settings,
        theory=TheoryService(settings),
        stockfish=StockfishService(settings),
        rag=RagService(settings),
        youtube=YoutubeService(settings),
        mongo=MongoService(settings),
    )
    return ChessAgent(deps)
