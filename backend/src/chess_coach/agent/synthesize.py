"""Turn the gathered facts into a natural-language recommendation (French).

By default the recommendation is built from a deterministic template, so the
agent runs without any paid LLM key. When ``LLM_ENABLED`` is set and a key is
configured, an OpenAI-compatible model phrases a richer answer from the same
facts; any failure falls back to the template.
"""

from __future__ import annotations

import logging

from chess_coach.agent.state import AgentState
from chess_coach.config import Settings

logger = logging.getLogger(__name__)


def format_evaluation(evaluation: dict | None) -> str:
    """Render a Stockfish evaluation as readable French."""

    if not evaluation:
        return ""
    if evaluation.get("evaluation_type") == "mate":
        return f"mat en {abs(evaluation.get('value', 0))} coups"
    pawns = evaluation.get("value", 0) / 100
    side = "les Blancs" if pawns >= 0 else "les Noirs"
    return f"évaluation de {pawns:+.2f} en faveur de {side}"


def _top_moves(state: AgentState, limit: int = 3) -> list[str]:
    return [move["san"] for move in state.get("theory_moves", [])[:limit]]


def build_template_recommendation(state: AgentState) -> str:
    """Build the deterministic French recommendation."""

    parts: list[str] = []

    if state.get("in_theory"):
        opening = state.get("opening_name") or "une ouverture connue"
        eco = state.get("opening_eco")
        label = f"**{opening}** ({eco})" if eco else f"**{opening}**"
        parts.append(f"Cette position relève de {label}.")
        moves = _top_moves(state)
        if moves:
            parts.append("Les coups théoriques principaux sont : " + ", ".join(moves) + ".")
    else:
        parts.append(
            "Cette position sort de la théorie connue : c'est un écart par rapport "
            "aux sentiers battus."
        )
        evaluation = state.get("evaluation")
        if evaluation:
            best = evaluation.get("best_move_san") or evaluation.get("best_move")
            parts.append(
                f"L'analyse du moteur Stockfish recommande {best} "
                f"({format_evaluation(evaluation)})."
            )

    passages = state.get("passages") or []
    if passages:
        snippet = passages[0]["text"].replace("\n", " ").strip()
        if len(snippet) > 280:
            snippet = snippet[:280].rstrip() + "…"
        parts.append("Pour approfondir : " + snippet)

    videos = state.get("videos") or []
    if videos:
        parts.append(f"{len(videos)} vidéo(s) explicative(s) vous sont proposées ci-dessous.")

    return "\n\n".join(parts)


def _build_llm_prompt(state: AgentState) -> str:
    """Build the LLM prompt with the position context, Kaggle-arena style."""

    position = state.get("position", {})
    lines = [
        "Tu es un entraîneur d'échecs pour les jeunes espoirs d'un club. "
        "Explique la position de manière claire.",
        "",
        f"FEN : {state.get('fen')}",
        f"Trait aux : {position.get('side_to_move')}",
        f"Échiquier :\n{position.get('board_ascii', '')}",
    ]
    if state.get("in_theory"):
        lines.append(f"Ouverture : {state.get('opening_name')}")
        lines.append("Coups théoriques : " + ", ".join(_top_moves(state, limit=5)))
    else:
        lines.append("La position est hors théorie.")
        lines.append(f"Moteur Stockfish : {format_evaluation(state.get('evaluation'))}")
    passages = state.get("passages") or []
    if passages:
        lines.append("Contexte (base de connaissances) : " + passages[0]["text"])
    lines.append("")
    lines.append("Rédige une recommandation de 4 à 6 phrases, en français.")
    return "\n".join(lines)


def _llm_recommendation(state: AgentState, settings: Settings) -> str:
    """Phrase the recommendation with an OpenAI-compatible model."""

    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=0.3,
        timeout=settings.http_timeout,
    )
    response = model.invoke(_build_llm_prompt(state))
    return str(response.content).strip()


def build_recommendation(state: AgentState, settings: Settings) -> str:
    """Return the final recommendation, using the LLM when enabled."""

    if settings.llm_enabled and settings.llm_api_key:
        try:
            return _llm_recommendation(state, settings)
        except Exception as exc:  # pragma: no cover - network/credentials
            # Never fail the answer because of the optional LLM layer.
            logger.warning("LLM synthesis failed, using the template: %s", exc)
    return build_template_recommendation(state)
