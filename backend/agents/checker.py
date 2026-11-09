"""Checker Agent.

Owns assessment. It:
  * picks verification questions to test a suspected gap,
  * decides whether the student's responses support the suspicion,
  * updates skill mastery (the only agent allowed to),
  * schedules and evaluates the later retest.

All decisions are rule-based and auditable; no LLM is involved in grading.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from ..content import misconceptions, questions_in_pool, skill_name

NAME = "Checker"
N_VERIFICATION = 2
N_RETEST = 3


# ---------------------------------------------------------------- selection

def select_verification(gap_skill: str, seen_ids: set[str]) -> dict:
    pool = [q for q in questions_in_pool(f"verification:{gap_skill}") if q["id"] not in seen_ids]
    same = [q for q in pool if q.get("check_role") == "same_type"]
    similar = [q for q in pool if q.get("check_role") == "similar_concept"]
    picked = []
    if same:
        picked.append(same[0])
    if similar:
        picked.append(similar[0])
    for q in pool:
        if len(picked) >= N_VERIFICATION:
            break
        if q not in picked:
            picked.append(q)
    if not picked:
        return {"agent": NAME, "ok": False,
                "reason": f"No unseen verification questions available for {skill_name(gap_skill)}."}
    return {
        "agent": NAME, "ok": True, "gap_skill": gap_skill,
        "question_ids": [q["id"] for q in picked[:N_VERIFICATION]],
        "rationale": [
            {"question_id": q["id"], "role": q.get("check_role", "same_type"),
             "why": "New question of the same kind as the mistakes" if q.get("check_role") == "same_type"
             else "Similar concept, tests the same underlying skill a different way"}
            for q in picked[:N_VERIFICATION]
        ],
    }


def select_retest(gap_skill: str, seen_ids: set[str]) -> dict:
    pool = [q for q in questions_in_pool(f"retest:{gap_skill}") if q["id"] not in seen_ids]
    if not pool:
        return {"agent": NAME, "ok": False, "reason": "No unseen retest questions left for this skill."}
    return {"agent": NAME, "ok": True, "question_ids": [q["id"] for q in pool[:N_RETEST]]}


def retest_available_at(delay_hours: float, now: Optional[datetime] = None) -> str:
    now = now or datetime.now(timezone.utc)
    return (now + timedelta(hours=delay_hours)).replace(microsecond=0).isoformat()


# ---------------------------------------------------------------- evaluation

def _supports(gap: dict, r: dict) -> bool:
    """Does a wrong answer support the suspected gap?"""
    if r["is_correct"]:
        return False
    if gap.get("misconception") is None:
        return True  # unclassified gap: any error on the target skill counts
    code = r.get("pattern")
    mis = misconceptions()
    return code == gap["misconception"] or (code in mis and mis[code]["gap_skill"] == gap["skill_id"])


def evaluate_verification(gap: dict, responses: list[dict]) -> dict:
    supporting = [r for r in responses if _supports(gap, r)]
    correct = [r for r in responses if r["is_correct"]]
    other = [r for r in responses if not r["is_correct"] and r not in supporting]

    if supporting and len(supporting) >= len(correct):
        verdict = "confirmed"
        reason = (f"{len(supporting)} of {len(responses)} new question(s) showed the same kind of mistake. "
                  "The suspected gap is supported by the evidence.")
    elif not supporting and not other:
        verdict = "rejected"
        reason = ("The student answered all verification questions correctly, so the earlier mistakes are not "
                  "explained by this gap (possibly a slip). The plan will not be changed.")
    else:
        verdict = "inconclusive"
        reason = (f"Mixed evidence: {len(supporting)} supporting, {len(correct)} correct, {len(other)} other "
                  "mistake(s). Sent to a teacher for review instead of acting on a guess.")
    return {
        "agent": NAME,
        "verdict": verdict,
        "reason": reason,
        "counts": {"supporting": len(supporting), "correct": len(correct), "other_wrong": len(other),
                   "total": len(responses)},
        "evidence": [{"question_id": r["question_id"], "prompt": r["prompt"], "answer": r["answer"],
                      "is_correct": bool(r["is_correct"]), "pattern": r.get("pattern"),
                      "supports_gap": r in supporting} for r in responses],
    }


def evaluate_retest(gap: dict, responses: list[dict], verification_rate: Optional[float]) -> dict:
    total = len(responses)
    correct = sum(1 for r in responses if r["is_correct"])
    rate = correct / total if total else 0.0
    repeated = sum(1 for r in responses if _supports(gap, r))
    passed = total > 0 and correct >= 2 and correct / total >= 2 / 3
    return {
        "agent": NAME,
        "passed": passed,
        "new_gap_status": "resolved" if passed else "still_present",
        "score": {"correct": correct, "total": total, "rate": round(rate, 3)},
        "verification_rate": None if verification_rate is None else round(verification_rate, 3),
        "improvement_points": None if verification_rate is None else round((rate - verification_rate) * 100),
        "repeated_mistake_pattern": repeated,
        "reason": (f"{correct}/{total} correct on new questions. "
                   + ("Meets the 2/3 mastery threshold." if passed else "Below the 2/3 mastery threshold; more practice planned.")),
    }


# ---------------------------------------------------------------- mastery

def mastery_updates(responses: list[dict], kind: str, gap_skill: Optional[str] = None,
                    retest_passed: Optional[bool] = None) -> dict[str, dict]:
    """Return {skill_id: {status, correct, attempts}} deltas from an assessment.

    Rules: one assessment can show 'needs_practice' or 'developing'. Only a
    passed retest (delayed, new questions) can mark a skill 'mastered'.
    """
    by_skill: dict[str, list[dict]] = {}
    for r in responses:
        by_skill.setdefault(r["skill_id"], []).append(r)
    out: dict[str, dict] = {}
    for skill, rs in by_skill.items():
        c = sum(1 for r in rs if r["is_correct"])
        if kind == "retest":
            status = "mastered" if c == len(rs) else ("developing" if c else "needs_practice")
        else:
            status = "developing" if c == len(rs) else "needs_practice"
        out[skill] = {"status": status, "correct": c, "attempts": len(rs)}
    if gap_skill and kind in ("verification", "retest"):
        # every verification/retest question targets the gap skill, so it counts as evidence for it
        c_all = sum(1 for r in responses if r["is_correct"])
        if kind == "verification":
            status = "needs_practice" if c_all < len(responses) else "developing"
        else:
            status = "mastered" if retest_passed else "needs_practice"
        out[gap_skill] = {"status": status, "correct": c_all, "attempts": len(responses)}
    return out
