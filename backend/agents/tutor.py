"""Tutor Agent.

Builds the lesson for the Planner's focus skill: small steps, worked examples
(computed exactly by the fractions engine), a note that refers to the student's
own mistake, and practice questions with hints.

The Tutor does NOT judge whether teaching worked. Practice answers are recorded
for the student's benefit, but mastery and gap status are decided only by the
Checker's later retest.

If an LLM is configured it may rewrite the personal note and the steps. Its
output is schema-validated and every arithmetic statement in it (like
"1/2 + 1/3 = 5/6") is re-checked with exact fractions; any error means the
template is used instead.
"""
from __future__ import annotations

import json
import re
from fractions import Fraction
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from .. import llm
from ..content import lessons, misconceptions, public_question, questions_in_pool, skill_name
from ..fractions_engine import correct_answer, fmt, hints_for, render_prompt, worked_solution

NAME = "Tutor"

_EQ_RE = re.compile(r"(\d+)\s*/\s*(\d+)\s*([+\-−×x*])\s*(\d+)\s*/\s*(\d+)\s*=\s*(\d+)(?:\s*/\s*(\d+))?")


def arithmetic_errors(text: str) -> list[str]:
    """Find 'a/b op c/d = e/f' statements in text and return the false ones."""
    bad = []
    for m in _EQ_RE.finditer(text):
        a = Fraction(int(m.group(1)), int(m.group(2))) if int(m.group(2)) else None
        b = Fraction(int(m.group(4)), int(m.group(5))) if int(m.group(5)) else None
        den = int(m.group(7)) if m.group(7) else 1
        if a is None or b is None or den == 0:
            bad.append(m.group(0))
            continue
        rhs = Fraction(int(m.group(6)), den)
        op = m.group(3)
        val = a + b if op == "+" else a - b if op in "-−" else a * b
        if val != rhs:
            bad.append(m.group(0))
    return bad


class _LLMLesson(BaseModel):
    personal_note: str = Field(min_length=20, max_length=400)
    steps: list[str] = Field(min_length=3, max_length=7)

    @field_validator("steps")
    @classmethod
    def step_lengths(cls, v: list[str]) -> list[str]:
        for s in v:
            if not 5 <= len(s) <= 260:
                raise ValueError("each step must be 5-260 characters")
        return v


def _template_note(gap: dict, focus: str) -> str:
    ev = (gap.get("evidence") or {}).get("diagnosis") or []
    mis = misconceptions().get(gap.get("misconception") or "")
    if ev and mis:
        e = ev[0]
        return (f"Earlier you answered {e['prompt'].replace(' = ?', '')} with {e['answer']}. "
                f"That matches a common mistake: \"{mis['label']}\". Lots of students do this. "
                f"Let's see why it doesn't work and fix it step by step.")
    return f"Let's build up '{skill_name(focus)}' step by step."


def run(payload: dict) -> dict:
    """payload = {focus_skill, gap: {...}, student: {grade}, practice_exclude: [ids]}"""
    focus = payload["focus_skill"]
    gap = payload["gap"]
    content = lessons().get(focus)
    if content is None:
        raise ValueError(f"No lesson content for skill '{focus}'.")

    examples = []
    for ex in content["worked_examples"]:
        q = {"id": "example", **ex}
        examples.append({"prompt": render_prompt(q), "steps": worked_solution(q), "answer": fmt(correct_answer(q))})

    exclude = set(payload.get("practice_exclude", []))
    practice_pool = questions_in_pool(f"practice:{focus}") or questions_in_pool(f"practice:{gap['skill_id']}")
    practice = [q for q in practice_pool if q["id"] not in exclude]
    practice_items = [{**public_question(q), "hint_count": len(hints_for(q))} for q in practice]

    note = _template_note(gap, focus)
    steps = list(content["steps"])
    source, llm_note = "template", None
    try:
        out = llm.complete_json(_SYSTEM, _user_prompt(payload, content, note), _LLMLesson, max_tokens=700)
        bad = arithmetic_errors(out.personal_note + "\n" + "\n".join(out.steps))
        if bad:
            raise llm.LLMError(f"arithmetic check failed on: {bad[:2]}")
        note, steps, source = out.personal_note, out.steps, "llm"
    except llm.LLMUnavailable as e:
        llm_note = f"Template lesson (no AI model configured: {e})."
    except llm.LLMError as e:
        llm_note = f"AI model output rejected, template lesson used: {e}"

    return {
        "agent": NAME,
        "skill_id": focus,
        "skill_name": skill_name(focus),
        "title": content["title"],
        "big_idea": content["big_idea"],
        "personal_note": note,
        "steps": steps,
        "sense_check": content["sense_check"],
        "worked_examples": examples,
        "practice": practice_items,
        "source": source,
        "llm_note": llm_note,
        "grading_note": "Practice answers are checked so you get feedback, but they don't change your progress. "
                        "The Checker decides that with a separate retest.",
    }


_SYSTEM = (
    "You are a patient maths tutor for school students (grades 3-6). Rewrite a short lesson so it speaks "
    "directly to this student's mistake. Use very simple words and short sentences. Do not include new worked "
    "examples with different numbers; if you mention a calculation, it must be exactly correct. "
    "Reply with only JSON: {\"personal_note\": \"2-3 sentences\", \"steps\": [\"3 to 7 short steps\"]}"
)


def _user_prompt(payload: dict, content: dict, template_note: str) -> str:
    gap = payload["gap"]
    return json.dumps({
        "student_grade": payload.get("student", {}).get("grade"),
        "skill": content["title"],
        "big_idea": content["big_idea"],
        "student_mistake_summary": template_note,
        "suspected_pattern": (misconceptions().get(gap.get("misconception") or "") or {}).get("label"),
        "template_steps": content["steps"],
    }, ensure_ascii=False)
