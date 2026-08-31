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
import re
from dataclasses import dataclass

from pydantic import BaseModel, Field

from chess_coach.agent.state import AgentState
from chess_coach.config import Settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Recommendation:
    """What the coach hands to the player, and how it was produced."""

    # Deux ou trois phrases sur l'ouverture reconnue : ce qu'elle est, son idée.
    opening_summary: str
    # Le conseil sur la position courante.
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


def build_template_opening_summary(state: AgentState) -> str:
    """Present the detected opening from the facts alone, without a model.

    This is the fallback used when no language model is configured. It stays
    factual: the name, the ECO code, how many master games reached the
    position, and the passage retrieved from the knowledge base when it really
    concerns this opening.
    """

    opening = state.get("opening_name")
    if not opening:
        return ""

    eco = state.get("opening_eco")
    phrases = [f"Ouverture détectée : {opening}" + (f" (code ECO {eco})." if eco else ".")]

    parties = state.get("total_games", 0)
    if parties:
        phrases.append(f"{parties:n} parties de maîtres ont atteint cette position.")

    passage = _matching_passage(state)
    if passage:
        phrases.append(passage)

    return " ".join(phrases)


# Ces mots reviennent dans la moitié des noms d'ouverture. Les compter comme
# une correspondance rapprocherait « King's Gambit » de « Queen's Gambit », ou
# « Défense française » de « Défense sicilienne ».
MOTS_GENERIQUES = {
    "attack",
    "attaque",
    "chess",
    "counter",
    "defence",
    "defense",
    "défense",
    "gambit",
    "game",
    "jeu",
    "opening",
    "ouverture",
    "partie",
    "pawn",
    "pion",
    "system",
    "système",
    "variante",
    "variation",
}


def _mots_significatifs(nom: str) -> set[str]:
    """Return the words of an opening name that actually identify it."""

    mots = re.split(r"[^\w]+", nom.lower())
    return {mot for mot in mots if len(mot) > 3 and mot not in MOTS_GENERIQUES}


def _matching_passage(state: AgentState, max_chars: int = 320) -> str:
    """Return the retrieved passage that really talks about this opening.

    The knowledge base answers for every query, so a passage is only used as a
    definition when its article shares an identifying word with the detected
    opening. Otherwise the presentation would describe the wrong opening, which
    is worse than saying nothing.
    """

    mots = _mots_significatifs(state.get("opening_name") or "")
    if not mots:
        return ""

    for passage in state.get("passages") or []:
        if mots & _mots_significatifs(passage.get("opening", "")):
            texte = passage["text"].replace("\n", " ").strip()
            return texte[:max_chars].rstrip() + ("…" if len(texte) > max_chars else "")
    return ""


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
    "Tu produis deux textes distincts :\n"
    "1. presentation_ouverture — deux ou trois phrases sur l'ouverture qui "
    "vient d'être reconnue : ce qu'elle est, d'où vient son nom si c'est "
    "parlant, et l'idée que poursuit le camp qui la joue. Si aucune ouverture "
    "n'est nommée, renvoie une chaîne vide.\n"
    "2. recommandation — le conseil sur la position courante.\n"
    "\n"
    "Règles de rédaction :\n"
    "- écris en français, sans titre ni liste ; la recommandation fait 4 à "
    "6 phrases, la présentation 2 à 3 ;\n"
    "- nomme les camps en français : « les Blancs », « les Noirs » ;\n"
    "- appuie-toi uniquement sur les éléments fournis ;\n"
    "- ne cite que les coups qui te sont donnés, n'en invente aucun ;\n"
    "- ne parle du moteur d'analyse que si une évaluation figure dans les "
    "éléments fournis ; sinon, n'y fais aucune allusion ;\n"
    "- explique en priorité le coup mis en avant dans l'interface : c'est "
    "celui que le joueur a sous les yeux ;\n"
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
            # L'interface met le premier coup en avant sous le titre « Prochain
            # coup ». Le dire au modèle évite qu'il commente un autre coup que
            # celui que le joueur a sous les yeux.
            lines.append(
                f"Coup mis en avant dans l'interface : {moves[0]['san']}, "
                "le plus joué en parties de maîtres."
            )
        games = state.get("reference_games") or []
        if games:
            lines.append("Parties de référence :")
            for game in games[:3]:
                lines.append(
                    f"  - {game['white']} - {game['black']}, {game['result']}, {game.get('year')}"
                )
        lines.append("Le moteur d'analyse n'a pas été sollicité : la position est dans la théorie.")
    else:
        lines.append("La position n'est pas de la théorie établie.")
        nom = state.get("opening_name")
        parties = state.get("total_games", 0)
        if nom and parties:
            lines.append(
                f"Elle porte tout de même un nom — {nom} — mais seules "
                f"{parties} parties de maîtres l'ont atteinte."
            )
        evaluation = state.get("evaluation")
        if evaluation:
            best = evaluation.get("best_move_san") or evaluation.get("best_move")
            lines.append(
                f"Moteur Stockfish : meilleur coup {best}, {format_evaluation(evaluation)}"
            )
            lines.append(f"Coup mis en avant dans l'interface : {best}.")

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


class CoachAnswer(BaseModel):
    """The two texts asked of the model, in one call."""

    presentation_ouverture: str = Field(
        description="Deux ou trois phrases sur l'ouverture reconnue, vide si aucune."
    )
    recommandation: str = Field(description="Le conseil sur la position courante.")


def _llm_answer(state: AgentState, settings: Settings) -> CoachAnswer:
    """Ask an OpenAI-compatible model for both texts at once.

    A structured answer avoids parsing a single block of prose, and one call
    keeps the latency where a second one would double it.
    """

    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=0.3,
        timeout=settings.llm_timeout,
    )
    answer = model.with_structured_output(CoachAnswer).invoke(
        [
            ("system", SYSTEM_PROMPT),
            ("human", build_llm_prompt(state)),
        ]
    )
    if not answer or not answer.recommandation.strip():
        raise ValueError("the model returned an empty answer")
    return answer


def build_recommendation(state: AgentState, settings: Settings) -> Recommendation:
    """Return what the coach says, using the model when it is available."""

    if settings.llm_enabled and settings.llm_api_key:
        try:
            answer = _llm_answer(state, settings)
            return Recommendation(
                opening_summary=answer.presentation_ouverture.strip(),
                text=answer.recommandation.strip(),
                used_llm=True,
            )
        except Exception as exc:  # pragma: no cover - network/credentials
            # An answer is more useful than an error: fall back on the template.
            logger.warning("LLM synthesis failed, using the template: %s", exc)
    return Recommendation(
        opening_summary=build_template_opening_summary(state),
        text=build_template_recommendation(state),
        used_llm=False,
    )
