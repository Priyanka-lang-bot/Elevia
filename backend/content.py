"""Loads and validates the skill map, question bank and lesson content."""
from __future__ import annotations

import json
from functools import lru_cache

from .config import DATA_DIR
from .fractions_engine import (
    answer_input_kind,
    choices,
    render_prompt,
    validate_question,
)


@lru_cache(maxsize=1)
def skill_map() -> dict:
    data = json.loads((DATA_DIR / "skill_map.json").read_text(encoding="utf-8"))
    ids = {s["id"] for s in data["skills"]}
    for s in data["skills"]:
        for p in s["prerequisites"]:
            if p not in ids:
                raise ValueError(f"Skill {s['id']} has unknown prerequisite {p}")
    for code, m in data["misconceptions"].items():
        if m["gap_skill"] not in ids:
            raise ValueError(f"Misconception {code} points to unknown skill")
    _check_acyclic(data["skills"])
    return data


def _check_acyclic(skills: list[dict]) -> None:
    graph = {s["id"]: s["prerequisites"] for s in skills}
    state: dict[str, int] = {}

    def visit(n: str) -> None:
        if state.get(n) == 1:
            raise ValueError(f"Cycle in skill map at {n}")
        if state.get(n) == 2:
            return
        state[n] = 1
        for p in graph[n]:
            visit(p)
        state[n] = 2

    for n in graph:
        visit(n)


def skills_by_id() -> dict[str, dict]:
    return {s["id"]: s for s in skill_map()["skills"]}


def skill_name(skill_id: str) -> str:
    s = skills_by_id().get(skill_id)
    return s["name"] if s else skill_id


def misconceptions() -> dict[str, dict]:
    return skill_map()["misconceptions"]


@lru_cache(maxsize=1)
def questions() -> dict[str, dict]:
    data = json.loads((DATA_DIR / "questions.json").read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    known = set(skills_by_id())
    for q in data["questions"]:
        validate_question(q)
        if q["skill_id"] not in known:
            raise ValueError(f"Question {q['id']} uses unknown skill {q['skill_id']}")
        if q["id"] in out:
            raise ValueError(f"Duplicate question id {q['id']}")
        out[q["id"]] = q
    return out


def questions_in_pool(pool: str) -> list[dict]:
    return [q for q in questions().values() if q["pool"] == pool]


def public_question(q: dict) -> dict:
    """Question as sent to the student: no answer included."""
    return {
        "id": q["id"],
        "skill_id": q["skill_id"],
        "skill_name": skill_name(q["skill_id"]),
        "type": q["type"],
        "prompt": render_prompt(q),
        "input_kind": answer_input_kind(q),
        "choices": choices(q),
    }


@lru_cache(maxsize=1)
def lessons() -> dict[str, dict]:
    data = json.loads((DATA_DIR / "lessons.json").read_text(encoding="utf-8"))
    known = set(skills_by_id())
    for sid, lesson in data.items():
        if sid not in known:
            raise ValueError(f"Lesson for unknown skill {sid}")
        for ex in lesson["worked_examples"]:
            validate_question({"id": f"lesson-{sid}", "pool": "lesson", "skill_id": sid, **ex})
    return data


def validate_all() -> dict:
    """Load everything once; raises on any content error. Used at startup and in tests."""
    return {
        "skills": len(skill_map()["skills"]),
        "misconceptions": len(misconceptions()),
        "questions": len(questions()),
        "lessons": len(lessons()),
    }
