"""One entry point for question rendering and answer checking, whatever the subject.

Fraction question types go to fractions_engine (unchanged, exact Fraction arithmetic). Every other subject
uses generic_engine (multiple choice, exact numbers, accepted text answers, predict-the-output code).
"""
from __future__ import annotations

from . import fractions_engine as fe
from . import generic_engine as ge

FRACTION_TYPES = ("add", "sub", "multiply", "simplify", "equivalent", "compare", "lcd")


def _e(q: dict):
    if q["type"] in FRACTION_TYPES:
        return fe
    if q["type"] in ge.TYPES:
        return ge
    raise ValueError(f"Question {q.get('id', '?')}: unknown type {q['type']}")


def render_prompt(q: dict) -> str:
    return _e(q).render_prompt(q)


def answer_input_kind(q: dict) -> str:
    return _e(q).answer_input_kind(q)


def choices(q: dict) -> list[str]:
    return _e(q).choices(q)


def correct_answer_text(q: dict) -> str:
    return _e(q).correct_answer_text(q)


def check_answer(q: dict, raw: str):
    return _e(q).check_answer(q, raw)


def hints_for(q: dict) -> list[str]:
    return _e(q).hints_for(q)


def worked_solution(q: dict) -> list[str]:
    return _e(q).worked_solution(q)


def validate_question(q: dict) -> None:
    _e(q).validate_question(q)


def is_fraction(q: dict) -> bool:
    return q["type"] in FRACTION_TYPES
