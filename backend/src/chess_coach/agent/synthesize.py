"""Turn the gathered facts into a natural-language recommendation (French).

The agent's last node hands the young player a short written explanation. It is
produced by a language model, prompted with everything the previous nodes
collected: the position, the theory or the engine verdict, the retrieved
knowledge and the reference games.

The position is described to the model the way the Kaggle "Game Arena" experi-
ments describe it — board diagram, side to move, legal moves — because a raw
FEN string alone is a poor input for a language model.

A deterministic French template stands behind the model. It is used when no key
is configured and whenever the call fails, so the agent always answers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from chess_coach.agent.state import AgentState
from chess_coach.config import Settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Recommendation:
    """The text handed to the player, and how it was produced."""

    text: str
    used_llm: bool


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


# --------------------------------------------------------------------------
# The deterministic template
# --------------------------------------------------------------------------


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


# --------------------------------------------------------------------------
# The language model
# --------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "Tu es entraîneur d'échecs pour les jeunes espoirs d'un club. "
    "Tu expliques les ouvertures de façon claire et "
    "encourageante, à un joueur de 10 à 16 ans qui découvre la théorie.\n"
    "\n"
    "Règles de rédaction :\n"
    "- réponds en français, en 4 à 6 phrases, sans titre ni liste ;\n"
    "- appuie-toi uniquement sur les éléments fournis ;\n"
    "- ne cite que les coups qui te sont donnés, n'en invente aucun ;\n"
    "- ne parle du moteur d'analyse que si une évaluation figure dans les "
    "éléments fournis ; sinon, n'y fais aucune allusion ;\n"
    "- nomme l'ouverture quand elle est connue et explique l'idée du coup "
    "principal (le plan, la case visée), pas seulement son nom ;\n"
    "- si la position est hors théorie, dis-le franchement et explique ce que "
    "propose le moteur ;\n"
    "- termine par un conseil concret à retenir."
)


def build_llm_prompt(state: AgentState) -> str:
    """Assemble everything the nodes collected into a single prompt."""

    position = state.get("position", {})
    lines = [
        f"FEN : {state.get('fen')}",
        f"Trait aux : {position.get('side_to_move')}",
        f"Coups légaux : {', '.join(position.get('legal_moves_san', [])[:12])}",
        "Échiquier :",
        str(position.get("board_ascii", "")),
        "",
    ]

    if state.get("in_theory"):
        lines.append(f"Ouverture : {state.get('opening_name')} ({state.get('opening_eco')})")
        moves = state.get("theory_moves", [])[:5]
        if moves:
            lines.append("Coups théoriques, avec le nombre de parties de maîtres :")
            for move in moves:
                lines.append(f"  - {move['san']} ({move.get('total', 0)} parties)")
        games = state.get("reference_games") or []
        if games:
            lines.append("Parties de référence :")
            for game in games[:3]:
                lines.append(
                    f"  - {game['white']} - {game['black']}, {game['result']}, {game.get('year')}"
                )
        lines.append("Le moteur d'analyse n'a pas été sollicité : la position est dans la théorie.")
    else:
        lines.append("La position est hors théorie connue.")
        evaluation = state.get("evaluation")
        if evaluation:
            best = evaluation.get("best_move_san") or evaluation.get("best_move")
            lines.append(
                f"Moteur Stockfish : meilleur coup {best}, {format_evaluation(evaluation)}"
            )

    passages = state.get("passages") or []
    if passages:
        lines.append("")
        lines.append("Extraits de la base de connaissances :")
        for passage in passages[:2]:
            text = passage["text"].replace("\n", " ").strip()
            lines.append(f"  - ({passage['opening']}) {text[:400]}")

    if state.get("videos"):
        lines.append("")
        lines.append(
            "Des vidéos explicatives sont affichées sous ta réponse : "
            "tu peux y renvoyer le joueur, sans citer de titre."
        )

    return "\n".join(lines)


def _llm_recommendation(state: AgentState, settings: Settings) -> str:
    """Ask an OpenAI-compatible model to phrase the recommendation."""

    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=0.3,
        timeout=settings.llm_timeout,
    )
    response = model.invoke(
        [
            ("system", SYSTEM_PROMPT),
            ("human", build_llm_prompt(state)),
        ]
    )
    text = str(response.content).strip()
    if not text:
        raise ValueError("the model returned an empty answer")
    return text


def build_recommendation(state: AgentState, settings: Settings) -> Recommendation:
    """Return the final recommendation, using the model when it is available."""

    if settings.llm_enabled and settings.llm_api_key:
        try:
            return Recommendation(text=_llm_recommendation(state, settings), used_llm=True)
        except Exception as exc:  # pragma: no cover - network/credentials
            # An answer is more useful than an error: fall back on the template.
            logger.warning("LLM synthesis failed, using the template: %s", exc)
    return Recommendation(text=build_template_recommendation(state), used_llm=False)
