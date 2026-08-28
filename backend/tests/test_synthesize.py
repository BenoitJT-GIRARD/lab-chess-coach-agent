"""Tests for the recommendation node (template and language model)."""

from __future__ import annotations

from typing import Any

import pytest

from chess_coach.agent import synthesize
from chess_coach.agent.synthesize import (
    build_llm_prompt,
    build_recommendation,
    build_template_recommendation,
)
from chess_coach.config import Settings

STATE_IN_THEORY: dict[str, Any] = {
    "fen": "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3",
    "in_theory": True,
    "opening_name": "Italian Game",
    "opening_eco": "C50",
    "position": {
        "side_to_move": "black",
        "legal_moves_san": ["Nf6", "Bc5", "d6"],
        "board_ascii": "r . b q k b n r",
    },
    "theory_moves": [
        {"san": "Nf6", "total": 103572421},
        {"san": "Bc5", "total": 101156348},
    ],
    "reference_games": [
        {"white": "Carlsen", "black": "Caruana", "result": "1-0", "year": 2019},
    ],
    "passages": [{"opening": "Giuoco Piano", "text": "Le fou en c4 vise la case f7."}],
    "videos": [{"title": "Tutoriel"}],
}

STATE_OUT_OF_THEORY: dict[str, Any] = {
    "fen": "rnbqkbnr/pppp1ppp/8/4p2Q/4P3/8/PPPP1PPP/RNB1KBNR b KQkq - 1 2",
    "in_theory": False,
    "position": {"side_to_move": "black", "legal_moves_san": ["Nc6"], "board_ascii": ""},
    "evaluation": {"evaluation_type": "cp", "value": 29, "best_move_san": "Nc6"},
    "passages": [],
    "videos": [],
}


class FakeModel:
    """Stands in for ChatOpenAI; records how it was called."""

    last_messages: Any = None

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    def invoke(self, messages: Any) -> Any:
        FakeModel.last_messages = messages

        class Answer:
            content = "Voici une explication rédigée par le modèle."

        return Answer()


class BrokenModel:
    """A model that always fails, to check the fallback."""

    def __init__(self, **kwargs: Any) -> None:
        pass

    def invoke(self, messages: Any) -> Any:
        raise RuntimeError("service unavailable")


def _use_model(monkeypatch: pytest.MonkeyPatch, model: type) -> None:
    """Replace the real ChatOpenAI, which synthesize imports on demand."""

    import langchain_openai

    monkeypatch.setattr(langchain_openai, "ChatOpenAI", model)


def test_the_template_names_the_opening_and_its_moves() -> None:
    text = build_template_recommendation(STATE_IN_THEORY)

    assert "Italian Game" in text
    assert "Nf6" in text
    assert "f7" in text  # le passage retrouvé est repris


def test_the_template_explains_an_out_of_theory_position() -> None:
    text = build_template_recommendation(STATE_OUT_OF_THEORY)

    assert "sort de la théorie" in text
    assert "Nc6" in text
    assert "+0.29" in text


def test_the_prompt_carries_the_position_and_the_facts() -> None:
    prompt = build_llm_prompt(STATE_IN_THEORY)

    # The position is described the way it is described to a language model in
    # the Kaggle Game Arena experiments: diagram, side to move, legal moves.
    assert "Trait aux : black" in prompt
    assert "Coups légaux : Nf6, Bc5, d6" in prompt
    assert "Italian Game (C50)" in prompt
    assert "103572421 parties" in prompt
    assert "Carlsen - Caruana, 1-0, 2019" in prompt
    assert "Le fou en c4 vise la case f7." in prompt


def test_without_a_key_the_template_is_used() -> None:
    settings = Settings(llm_enabled=True, llm_api_key="")

    recommendation = build_recommendation(STATE_IN_THEORY, settings)

    assert recommendation.used_llm is False
    assert "Italian Game" in recommendation.text


def test_with_a_key_the_model_writes_the_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_model(monkeypatch, FakeModel)
    settings = Settings(llm_enabled=True, llm_api_key="sk-test")

    recommendation = build_recommendation(STATE_IN_THEORY, settings)

    assert recommendation.used_llm is True
    assert recommendation.text == "Voici une explication rédigée par le modèle."
    # The system prompt sets the coaching role, the human message the facts.
    role, system = FakeModel.last_messages[0]
    assert role == "system"
    assert "entraîneur" in system


def test_a_failing_model_falls_back_on_the_template(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_model(monkeypatch, BrokenModel)
    settings = Settings(llm_enabled=True, llm_api_key="sk-test")

    recommendation = build_recommendation(STATE_IN_THEORY, settings)

    assert recommendation.used_llm is False
    assert "Italian Game" in recommendation.text


def test_the_synthesize_module_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    # Even an empty state must produce something readable.
    _use_model(monkeypatch, BrokenModel)

    recommendation = build_recommendation({}, Settings(llm_enabled=True, llm_api_key="sk-test"))

    assert isinstance(recommendation.text, str)
    assert synthesize.format_evaluation(None) == ""
