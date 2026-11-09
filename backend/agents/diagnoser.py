"""Diagnoser Agent.

Looks at a completed assessment and forms a HYPOTHESIS about the underlying
learning gap. It never marks a gap as confirmed: its output status is always
"suspected". Verification is the Checker's job.

The gap and confidence come from deterministic evidence (which mistake patterns
the exact-arithmetic engine detected, and how consistently). If an LLM is
configured it only rewrites the hypothesis in plain language; it cannot change
the skill, the confidence or the status.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from .. import llm
from ..content import misconceptions, skill_name

NAME = "Diagnoser"


def confidence_label(c: float) -> str:
    if c >= 0.7:
        return "high"
    if c >= 0.45:
        return "medium"
    return "low"


class _LLMHypothesis(BaseModel):
    hypothesis: str = Field(min_length=20, max_length=500)
    student_message: str = Field(min_length=10, max_length=300)

    @field_validator("hypothesis", "student_message")
    @classmethod
    def no_certainty_claims(cls, v: str) -> str:
        banned = ("confirmed", "diagnosed", "learning disability", "definitely", "proven")
        low = v.lower()
        for b in banned:
            if b in low:
                raise ValueError(f"must not claim certainty ('{b}')")
        return v


def run(payload: dict) -> dict:
    """payload = {student: {...}, responses: [ {question_id, skill_id, gap_targets, prompt,
    answer, is_correct, pattern, expected} ]}"""
    responses = payload["responses"]
    wrong = [r for r in responses if not r["is_correct"]]
    total, n_wrong = len(responses), len(wrong)
    base = {
        "agent": NAME,
        "score": {"correct": total - n_wrong, "total": total},
        "status": "suspected",
    }
    if n_wrong == 0:
        return {**base, "has_gap": False, "status": "none",
                "summary": "All answers correct. No learning gap suspected from this assessment.",
                "mode": "rules"}

    mis = misconceptions()
    # Count opportunities: how many questions could reveal a gap in each skill.
    opportunities: dict[str, int] = defaultdict(int)
    for r in responses:
        for g in r.get("gap_targets", []):
            opportunities[g] += 1

    candidates: dict[str, dict] = {}
    for r in wrong:
        code = r.get("pattern")
        if code in mis:
            skill = mis[code]["gap_skill"]
            c = candidates.setdefault(skill, {"skill_id": skill, "patterns": defaultdict(int), "evidence": [],
                                             "classified": True})
            c["patterns"][code] += 1
            c["evidence"].append(_evidence(r, mis[code]["label"]))
        else:
            skill = (r.get("gap_targets") or [r["skill_id"]])[0]
            c = candidates.setdefault(skill, {"skill_id": skill, "patterns": defaultdict(int), "evidence": [],
                                             "classified": False})
            c["evidence"].append(_evidence(r, "No known pattern matched"))

    scored = []
    for skill, c in candidates.items():
        hits = sum(c["patterns"].values())
        opp = max(opportunities.get(skill, 0), len(c["evidence"]), 1)
        if hits:
            conf = 0.35 + 0.25 * (hits - 1) + 0.2 * (hits / opp)
        else:
            conf = 0.2 + 0.05 * (len(c["evidence"]) - 1)
        conf = round(min(conf, 0.9), 2)
        top_pattern = max(c["patterns"], key=c["patterns"].get) if c["patterns"] else None
        scored.append({
            "skill_id": skill,
            "skill_name": skill_name(skill),
            "misconception": top_pattern,
            "misconception_label": mis[top_pattern]["label"] if top_pattern else None,
            "pattern_hits": hits,
            "opportunities": opp,
            "confidence": conf,
            "confidence_label": confidence_label(conf),
            "evidence": c["evidence"],
        })
    scored.sort(key=lambda x: (x["confidence"], x["pattern_hits"]), reverse=True)
    primary, others = scored[0], scored[1:]

    hypothesis = _template_hypothesis(primary)
    student_message = ("ELEVIA noticed something in your answers and wants to check it with a couple of "
                       "new questions before deciding anything.")
    alternatives = [
        {"skill_id": o["skill_id"], "skill_name": o["skill_name"], "confidence": o["confidence"],
         "confidence_label": o["confidence_label"], "misconception_label": o["misconception_label"]}
        for o in others
    ]
    if primary["pattern_hits"] <= 1:
        alternatives.append({"skill_id": None, "skill_name": "Careless slip",
                             "confidence": None, "confidence_label": "possible",
                             "misconception_label": "A single mistake can be a slip rather than a gap."})

    mode, llm_note = "rules", None
    try:
        out = llm.complete_json(_SYSTEM, _user_prompt(primary, payload), _LLMHypothesis, max_tokens=400)
        hypothesis, student_message = out.hypothesis, out.student_message
        mode = "rules+llm"
    except llm.LLMUnavailable as e:
        llm_note = f"Template wording used (no AI model configured: {e})."
    except llm.LLMError as e:
        llm_note = f"AI model output rejected, template wording used: {e}"

    return {
        **base,
        "has_gap": True,
        "primary": {**primary, "hypothesis": hypothesis},
        "student_message": student_message,
        "alternatives": alternatives,
        "mode": mode,
        "llm_note": llm_note,
    }


def _evidence(r: dict, label: str) -> dict:
    return {"question_id": r["question_id"], "prompt": r["prompt"], "answer": r["answer"],
            "expected": r["expected"], "pattern": r.get("pattern"), "observation": label}


def _template_hypothesis(p: dict) -> str:
    if p["misconception"]:
        ex = p["evidence"][0]
        mis = misconceptions()[p["misconception"]]
        return (f"Possible gap in '{p['skill_name']}'. On {p['pattern_hits']} of {p['opportunities']} relevant "
                f"question(s) the answer matched the pattern \"{mis['label']}\" "
                f"(e.g. {ex['prompt'].replace(' = ?', '')} answered as {ex['answer']}). {mis['explanation']} "
                f"This is a hypothesis to be checked, not a conclusion.")
    return (f"Possible gap in '{p['skill_name']}': {len(p['evidence'])} incorrect answer(s) did not match any "
            f"known mistake pattern, so the cause is unclear. Low confidence; needs checking.")


_SYSTEM = (
    "You are the Diagnoser in an educational system for school maths. You will be given structured evidence "
    "about a student's fraction mistakes that has ALREADY been analysed by exact arithmetic. Do not recompute "
    "or second-guess correctness. Write (1) a short hypothesis for the teacher (2-3 sentences) explaining the "
    "likely reason for the mistakes, framed as a possibility to be verified, and (2) one encouraging sentence "
    "for the student that says ELEVIA will check with a few more questions. Never say the gap is confirmed, "
    "never mention learning disabilities or medical terms. Reply with only JSON: "
    '{"hypothesis": "...", "student_message": "..."}'
)


def _user_prompt(primary: dict, payload: dict) -> str:
    import json
    return json.dumps({
        "student_grade": payload.get("student", {}).get("grade"),
        "suspected_skill": primary["skill_name"],
        "pattern": primary["misconception_label"],
        "confidence_label": primary["confidence_label"],
        "evidence": [{"question": e["prompt"], "student_answer": e["answer"], "correct_answer": e["expected"]}
                     for e in primary["evidence"]],
    }, ensure_ascii=False)
