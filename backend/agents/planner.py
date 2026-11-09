"""Planner Agent.

Receives a VERIFIED gap and builds a learning path by walking the skill map's
prerequisites. It refuses to run on an unverified gap, which is the main
guardrail stopping a Diagnoser guess from changing a student's plan.
"""
from __future__ import annotations

from typing import Optional

from ..content import lessons, skill_name, skills_by_id

NAME = "Planner"


class UnverifiedGapError(RuntimeError):
    pass


def _prereq_chain(skill_id: str) -> list[str]:
    """All prerequisites of skill_id, deepest first (topological order)."""
    skills = skills_by_id()
    order: list[str] = []
    seen: set[str] = set()

    def visit(s: str) -> None:
        for p in skills[s]["prerequisites"]:
            if p not in seen:
                seen.add(p)
                visit(p)
                order.append(p)

    visit(skill_id)
    return order


def _dependents_of(skill_id: str) -> set[str]:
    return {s["id"] for s in skills_by_id().values() if skill_id in _prereq_chain(s["id"])}


def run(payload: dict) -> dict:
    """payload = {gap: {...}, mastery: {skill_id: status}, failed_skills: [...],
    forced_focus: optional skill_id (teacher override), created_by: 'Planner' | 'teacher:<name>'}"""
    gap = payload["gap"]
    if gap["status"] not in ("confirmed", "still_present") or not gap.get("verified_by"):
        raise UnverifiedGapError(
            f"Planner refused: gap status is '{gap['status']}'. Only a gap verified by the Checker "
            "or a teacher can change the learning plan.")

    mastery: dict[str, str] = payload.get("mastery", {})
    teachable = set(lessons())
    gap_skill = gap["skill_id"]
    path: list[dict] = []
    watch: list[dict] = []

    for p in _prereq_chain(gap_skill):
        st = mastery.get(p, "not_assessed")
        if st == "needs_practice":
            path.append({"skill_id": p, "skill_name": skill_name(p), "reason": "Earlier skill that also showed errors",
                         "has_lesson": p in teachable})
        elif st == "not_assessed":
            watch.append({"skill_id": p, "skill_name": skill_name(p), "reason": "Not yet assessed"})

    path.append({"skill_id": gap_skill, "skill_name": skill_name(gap_skill),
                 "reason": "Verified learning gap", "has_lesson": gap_skill in teachable})

    deps = _dependents_of(gap_skill)
    for f in payload.get("failed_skills", []):
        if f in deps and all(x["skill_id"] != f for x in path):
            path.append({"skill_id": f, "skill_name": skill_name(f),
                         "reason": "Original task: apply the skill here once the gap is closed",
                         "has_lesson": f in teachable})

    forced = payload.get("forced_focus")
    if forced:
        if forced not in teachable:
            raise ValueError(f"No lesson content for '{forced}'.")
        focus = forced
        if all(x["skill_id"] != forced for x in path):
            path.insert(0, {"skill_id": forced, "skill_name": skill_name(forced),
                            "reason": "Chosen by teacher", "has_lesson": True})
        rationale = f"Teacher override: focus set to '{skill_name(forced)}'."
    else:
        focus_item = next((x for x in path if x["has_lesson"]), None)
        if focus_item is None:
            raise ValueError("No teachable skill on the path.")
        focus = focus_item["skill_id"]
        rationale = (f"The Checker verified a gap in '{skill_name(gap_skill)}'. "
                     + (f"Starting with '{skill_name(focus)}' because it is an earlier skill that also showed errors."
                        if focus != gap_skill else
                        f"Its prerequisites show no errors, so we start directly with '{skill_name(focus)}'."))

    return {
        "agent": NAME,
        "focus_skill": focus,
        "focus_skill_name": skill_name(focus),
        "path": path,
        "watch": watch,
        "rationale": rationale,
        "created_by": payload.get("created_by", NAME),
    }
