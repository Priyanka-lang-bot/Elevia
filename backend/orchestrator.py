"""Python orchestrator: runs the learning workflow and passes structured JSON
between the four agents through the shared student learning record (SQLite).

Stages of a learning case:
  diagnostic -> verification -> learning -> retest_pending -> retest -> completed
  side exits: closed (no gap / gap rejected), teacher_review (inconclusive or blocked)

Every agent call is written to agent_runs with its exact input and output,
which is what the Agent Activity page shows.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from . import db
from .agents import checker, diagnoser, planner, tutor
from .config import get_settings
from .content import lessons, public_question, questions, skill_name, skills_by_id
from .db import dumps, now_iso, row_to_dict, rows_to_dicts
from .fractions_engine import check_answer, correct_answer_text, hints_for, render_prompt, worked_solution

ACTIVE_STAGES = ("diagnostic", "verification", "learning", "retest_pending", "retest", "teacher_review")


class WorkflowError(Exception):
    """A request that is not valid in the current state (maps to HTTP 409/400)."""

    def __init__(self, message: str, status_code: int = 409):
        super().__init__(message)
        self.status_code = status_code


class NotFound(WorkflowError):
    def __init__(self, message: str):
        super().__init__(message, 404)


# ======================================================================
# helpers
# ======================================================================

def _get(conn, table: str, id_: int) -> dict:
    row = row_to_dict(conn.execute(f"SELECT * FROM {table} WHERE id = ?", (id_,)).fetchone())
    if row is None:
        raise NotFound(f"{table[:-1].capitalize()} {id_} not found")
    return row


def _set_stage(conn, case_id: int, stage: str, closed_reason: Optional[str] = None) -> None:
    conn.execute("UPDATE cases SET stage = ?, updated_at = ?, closed_reason = COALESCE(?, closed_reason) WHERE id = ?",
                 (stage, now_iso(), closed_reason, case_id))


def _run_agent(conn: sqlite3.Connection, case_id: int, agent: str, step: str, payload: Any,
               fn: Callable[[], dict]) -> dict:
    cur = conn.execute(
        "INSERT INTO agent_runs (case_id, agent, step, status, mode, input, started_at) VALUES (?,?,?,?,?,?,?)",
        (case_id, agent, step, "running", "pending", dumps(payload), now_iso()))
    run_id = cur.lastrowid
    try:
        out = fn()
    except Exception as e:
        conn.execute("UPDATE agent_runs SET status='failed', error=?, mode='rules', finished_at=? WHERE id=?",
                     (f"{type(e).__name__}: {e}", now_iso(), run_id))
        raise
    mode = out.get("mode") or out.get("source") or "rules"
    conn.execute("UPDATE agent_runs SET status='succeeded', mode=?, output=?, finished_at=? WHERE id=?",
                 (mode, dumps(out), now_iso(), run_id))
    return out


def _log_skip(conn, case_id: int, agent: str, step: str, reason: str) -> None:
    t = now_iso()
    conn.execute(
        "INSERT INTO agent_runs (case_id, agent, step, status, mode, input, output, started_at, finished_at) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (case_id, agent, step, "skipped", "rules", dumps({}), dumps({"reason": reason}), t, t))


def _mastery_map(conn, student_id: int) -> dict[str, str]:
    rows = conn.execute("SELECT skill_id, status FROM skill_mastery WHERE student_id = ?", (student_id,)).fetchall()
    return {r["skill_id"]: r["status"] for r in rows}


def _apply_mastery(conn, student_id: int, updates: dict[str, dict]) -> None:
    for skill, u in updates.items():
        conn.execute(
            """INSERT INTO skill_mastery (student_id, skill_id, status, correct, attempts, updated_by, updated_at)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(student_id, skill_id) DO UPDATE SET
                 status = excluded.status,
                 correct = skill_mastery.correct + excluded.correct,
                 attempts = skill_mastery.attempts + excluded.attempts,
                 updated_by = excluded.updated_by,
                 updated_at = excluded.updated_at""",
            (student_id, skill, u["status"], u.get("correct", 0), u.get("attempts", 0), "Checker", now_iso()))


def _create_assessment(conn, case_id: int, kind: str, qids: list[str], available_at: Optional[str] = None) -> int:
    cur = conn.execute(
        "INSERT INTO assessments (case_id, kind, question_ids, status, available_at, created_at) VALUES (?,?,?,?,?,?)",
        (case_id, kind, dumps(qids), "open", available_at, now_iso()))
    return cur.lastrowid


def _enriched_responses(conn, assessment_id: int) -> list[dict]:
    qs = questions()
    out = []
    for r in rows_to_dicts(conn.execute(
            "SELECT * FROM responses WHERE assessment_id = ? ORDER BY id", (assessment_id,)).fetchall()):
        q = qs[r["question_id"]]
        out.append({
            "question_id": r["question_id"], "skill_id": r["skill_id"], "gap_targets": q.get("gap_targets", []),
            "prompt": render_prompt(q), "answer": r["answer_raw"], "is_correct": bool(r["is_correct"]),
            "pattern": r["pattern"], "expected": correct_answer_text(q), "hints_used": r["hints_used"],
        })
    return out


def _seen_question_ids(conn, student_id: int) -> set[str]:
    rows = conn.execute("SELECT DISTINCT question_id FROM responses WHERE student_id = ?", (student_id,)).fetchall()
    seen = {r["question_id"] for r in rows}
    # include questions already assigned in open assessments
    for a in conn.execute(
            "SELECT a.question_ids FROM assessments a JOIN cases c ON c.id = a.case_id WHERE c.student_id = ?",
            (student_id,)).fetchall():
        seen.update(json.loads(a["question_ids"]))
    return seen


def _current_gap(conn, case_id: int) -> Optional[dict]:
    return row_to_dict(conn.execute("SELECT * FROM gaps WHERE case_id = ? ORDER BY id DESC LIMIT 1",
                                    (case_id,)).fetchone())


def _active_plan(conn, case_id: int) -> Optional[dict]:
    return row_to_dict(conn.execute(
        "SELECT * FROM plans WHERE case_id = ? AND status = 'active' ORDER BY id DESC LIMIT 1", (case_id,)).fetchone())


# ======================================================================
# students and cases
# ======================================================================

def create_student(display_name: str, grade: int, is_sample: bool = False) -> dict:
    name = (display_name or "").strip()
    if not 1 <= len(name) <= 40:
        raise WorkflowError("Name must be 1-40 characters.", 400)
    if not 3 <= int(grade) <= 8:
        raise WorkflowError("Grade must be between 3 and 8.", 400)
    with db.transaction() as conn:
        cur = conn.execute("INSERT INTO students (display_name, grade, is_sample, created_at) VALUES (?,?,?,?)",
                           (name, int(grade), int(is_sample), now_iso()))
        return _get(conn, "students", cur.lastrowid)


def list_students() -> list[dict]:
    with db.transaction() as conn:
        return rows_to_dicts(conn.execute("SELECT * FROM students ORDER BY is_sample DESC, id").fetchall())


def get_student(student_id: int) -> dict:
    with db.transaction() as conn:
        return _get(conn, "students", student_id)


def start_case(student_id: int) -> dict:
    with db.transaction() as conn:
        _get(conn, "students", student_id)
        active = conn.execute(
            f"SELECT id FROM cases WHERE student_id = ? AND stage IN ({','.join('?' * len(ACTIVE_STAGES))}) "
            "ORDER BY id DESC LIMIT 1", (student_id, *ACTIVE_STAGES)).fetchone()
        if active:
            return case_detail(active["id"], conn)
        n_prev = conn.execute("SELECT COUNT(*) FROM cases WHERE student_id = ?", (student_id,)).fetchone()[0]
        dset = "A" if n_prev % 2 == 0 else "B"
        t = now_iso()
        cur = conn.execute(
            "INSERT INTO cases (student_id, stage, diagnostic_set, created_at, updated_at) VALUES (?,?,?,?,?)",
            (student_id, "diagnostic", dset, t, t))
        case_id = cur.lastrowid
        qids = sorted(q["id"] for q in questions().values() if q["pool"] == f"diagnostic:{dset}")
        _create_assessment(conn, case_id, "diagnostic", qids)
        return case_detail(case_id, conn)


# ======================================================================
# answering
# ======================================================================

def get_assessment(assessment_id: int) -> dict:
    with db.transaction() as conn:
        return _assessment_view(conn, _get(conn, "assessments", assessment_id))


def _assessment_view(conn, a: dict) -> dict:
    qs = questions()
    answered = {r["question_id"]: r for r in rows_to_dicts(conn.execute(
        "SELECT * FROM responses WHERE assessment_id = ?", (a["id"],)).fetchall())}
    reveal = a["kind"] == "practice" or a["status"] == "completed"
    items = []
    for qid in a["question_ids"]:
        q = qs[qid]
        item = public_question(q)
        r = answered.get(qid)
        item["answered"] = r is not None
        if r:
            item["your_answer"] = r["answer_raw"]
            item["is_correct"] = bool(r["is_correct"])
            if reveal:
                item["expected"] = correct_answer_text(q)
        if a["kind"] == "practice":
            item["hint_count"] = len(hints_for(q))
        items.append(item)
    return {**a, "questions": items, "answered": len(answered), "total": len(a["question_ids"])}


def submit_answer(assessment_id: int, question_id: str, answer: str, hints_used: int = 0) -> dict:
    with db.transaction() as conn:
        a = _get(conn, "assessments", assessment_id)
        if a["status"] != "open":
            raise WorkflowError("This assessment is already completed.")
        if a["available_at"] and a["available_at"] > now_iso():
            raise WorkflowError("This retest is not available yet.")
        if question_id not in a["question_ids"]:
            raise WorkflowError("That question is not part of this assessment.", 400)
        case = _get(conn, "cases", a["case_id"])
        q = questions()[question_id]
        res = check_answer(q, answer)
        if not res.valid:
            return {"accepted": False, "error": res.error}
        exists = conn.execute("SELECT 1 FROM responses WHERE assessment_id=? AND question_id=?",
                              (assessment_id, question_id)).fetchone()
        if exists:
            raise WorkflowError("You've already answered this question.")
        conn.execute(
            "INSERT INTO responses (assessment_id, student_id, question_id, skill_id, answer_raw, is_correct, "
            "pattern, hints_used, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (assessment_id, case["student_id"], question_id, q["skill_id"], str(answer).strip()[:20],
             int(res.correct), res.pattern, max(0, min(int(hints_used), 5)), now_iso()))

        feedback = {"accepted": True, "is_correct": res.correct, "notes": res.notes}
        if a["kind"] == "practice":
            # Practice: full feedback, worked solution. Recorded but not used for mastery.
            feedback["expected"] = res.expected
            feedback["solution"] = worked_solution(q)
        else:
            feedback["message"] = ("Correct." if res.correct else
                                   "Not quite. ELEVIA has recorded this and will look at your answers together.")

        n_answered = conn.execute("SELECT COUNT(*) FROM responses WHERE assessment_id=?",
                                  (assessment_id,)).fetchone()[0]
        completed = n_answered >= len(a["question_ids"])
        if completed:
            _complete_assessment(conn, a, case)
        feedback["assessment_completed"] = completed
        feedback["case"] = case_detail(case["id"], conn)
        return feedback


def get_hint(assessment_id: int, question_id: str, level: int) -> dict:
    with db.transaction() as conn:
        a = _get(conn, "assessments", assessment_id)
        if a["kind"] != "practice":
            raise WorkflowError("Hints are only available in the learning room.", 403)
        if question_id not in a["question_ids"]:
            raise WorkflowError("That question is not part of this practice set.", 400)
        hints = hints_for(questions()[question_id])
        level = max(1, min(int(level), len(hints)))
        return {"level": level, "total": len(hints), "hint": hints[level - 1], "agent": "Tutor"}


def finish_practice(assessment_id: int) -> dict:
    with db.transaction() as conn:
        a = _get(conn, "assessments", assessment_id)
        if a["kind"] != "practice" or a["status"] != "open":
            raise WorkflowError("No open practice set to finish.")
        n = conn.execute("SELECT COUNT(*) FROM responses WHERE assessment_id=?", (assessment_id,)).fetchone()[0]
        if n < 2:
            raise WorkflowError("Try at least 2 practice questions before finishing.", 400)
        case = _get(conn, "cases", a["case_id"])
        _complete_assessment(conn, a, case)
        return case_detail(case["id"], conn)


def _complete_assessment(conn, a: dict, case: dict) -> None:
    upd = conn.execute("UPDATE assessments SET status='completed', completed_at=? WHERE id=? AND status='open'",
                       (now_iso(), a["id"]))
    if upd.rowcount == 0:
        return  # already completed by a concurrent request
    kind = a["kind"]
    if kind == "diagnostic":
        _after_diagnostic(conn, a, case)
    elif kind == "verification":
        _after_verification(conn, a, case)
    elif kind == "practice":
        _after_practice(conn, a, case)
    elif kind == "retest":
        _after_retest(conn, a, case)


# ======================================================================
# workflow transitions
# ======================================================================

def _after_diagnostic(conn, a: dict, case: dict) -> None:
    responses = _enriched_responses(conn, a["id"])
    student = _get(conn, "students", case["student_id"])
    _apply_mastery(conn, student["id"], checker.mastery_updates(responses, "diagnostic"))

    payload = {"student": {"id": student["id"], "grade": student["grade"]}, "responses": responses}
    diag = _run_agent(conn, case["id"], "Diagnoser", "diagnose", payload, lambda: diagnoser.run(payload))
    if not diag["has_gap"]:
        _log_skip(conn, case["id"], "Checker", "verify", "No suspected gap to verify.")
        _set_stage(conn, case["id"], "closed", "no_gap_found")
        return

    p = diag["primary"]
    cur = conn.execute(
        "INSERT INTO gaps (case_id, skill_id, misconception, status, confidence, confidence_label, hypothesis, "
        "evidence, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (case["id"], p["skill_id"], p["misconception"], "suspected", p["confidence"], p["confidence_label"],
         p["hypothesis"], dumps({"diagnosis": p["evidence"], "alternatives": diag["alternatives"]}), now_iso()))
    gap_id = cur.lastrowid

    seen = _seen_question_ids(conn, student["id"])
    sel_in = {"gap_id": gap_id, "gap_skill": p["skill_id"], "exclude": sorted(seen)}
    sel = _run_agent(conn, case["id"], "Checker", "select_verification", sel_in,
                     lambda: checker.select_verification(p["skill_id"], seen))
    if not sel["ok"]:
        _set_stage(conn, case["id"], "teacher_review", sel["reason"])
        return
    _create_assessment(conn, case["id"], "verification", sel["question_ids"])
    _set_stage(conn, case["id"], "verification")


def _after_verification(conn, a: dict, case: dict) -> None:
    gap = _current_gap(conn, case["id"])
    responses = _enriched_responses(conn, a["id"])
    payload = {"gap": {k: gap[k] for k in ("id", "skill_id", "misconception", "status", "confidence")},
               "responses": responses}
    ev = _run_agent(conn, case["id"], "Checker", "evaluate_verification", payload,
                    lambda: checker.evaluate_verification(gap, responses))
    _apply_mastery(conn, case["student_id"],
                   checker.mastery_updates(responses, "verification", gap_skill=gap["skill_id"]))
    evidence = {**gap["evidence"], "verification": ev["evidence"], "verification_reason": ev["reason"]}
    conn.execute("UPDATE gaps SET status=?, evidence=?, verified_by=?, verified_at=? WHERE id=?",
                 (ev["verdict"], dumps(evidence), "Checker" if ev["verdict"] == "confirmed" else None,
                  now_iso(), gap["id"]))
    if ev["verdict"] == "confirmed":
        _safe_plan_and_teach(conn, case)
    elif ev["verdict"] == "rejected":
        _log_skip(conn, case["id"], "Planner", "plan", "Gap was not supported by verification; plan unchanged.")
        _set_stage(conn, case["id"], "closed", "gap_not_supported")
    else:
        _log_skip(conn, case["id"], "Planner", "plan", "Verification inconclusive; waiting for teacher review.")
        _set_stage(conn, case["id"], "teacher_review", "verification_inconclusive")


def _plan_and_teach(conn, case: dict, created_by: str, forced_focus: Optional[str] = None) -> None:
    gap = _current_gap(conn, case["id"])
    student = _get(conn, "students", case["student_id"])
    diag_a = row_to_dict(conn.execute(
        "SELECT * FROM assessments WHERE case_id=? AND kind='diagnostic' ORDER BY id LIMIT 1",
        (case["id"],)).fetchone())
    failed = sorted({r["skill_id"] for r in _enriched_responses(conn, diag_a["id"]) if not r["is_correct"]})
    payload = {
        "gap": {k: gap[k] for k in ("id", "skill_id", "misconception", "status", "verified_by")},
        "mastery": _mastery_map(conn, student["id"]),
        "failed_skills": failed,
        "forced_focus": forced_focus,
        "created_by": created_by,
    }
    plan = _run_agent(conn, case["id"], "Planner", "plan", payload, lambda: planner.run(payload))

    conn.execute("UPDATE plans SET status='replaced' WHERE case_id=? AND status='active'", (case["id"],))
    cur = conn.execute(
        "INSERT INTO plans (case_id, gap_id, focus_skill, path, rationale, status, created_by, created_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (case["id"], gap["id"], plan["focus_skill"], dumps({"path": plan["path"], "watch": plan["watch"]}),
         plan["rationale"], "active", created_by, now_iso()))
    plan_id = cur.lastrowid

    # close any open practice from a replaced plan
    conn.execute("UPDATE assessments SET status='completed', completed_at=? "
                 "WHERE case_id=? AND kind='practice' AND status='open'", (now_iso(), case["id"]))

    t_payload = {"focus_skill": plan["focus_skill"],
                 "gap": {k: gap[k] for k in ("skill_id", "misconception", "evidence")},
                 "student": {"grade": student["grade"]}}
    lesson = _run_agent(conn, case["id"], "Tutor", "teach", t_payload, lambda: tutor.run(t_payload))
    conn.execute("INSERT INTO lessons (case_id, plan_id, skill_id, content, source, created_at) VALUES (?,?,?,?,?,?)",
                 (case["id"], plan_id, lesson["skill_id"], dumps(lesson), lesson["source"], now_iso()))
    _create_assessment(conn, case["id"], "practice", [p["id"] for p in lesson["practice"]])
    _set_stage(conn, case["id"], "learning")


def _safe_plan_and_teach(conn, case: dict) -> None:
    """Automatic planning; if it fails, hand the case to a teacher instead of crashing."""
    try:
        _plan_and_teach(conn, case, created_by="Planner")
    except Exception as e:  # failure is already recorded in agent_runs
        _set_stage(conn, case["id"], "teacher_review", f"planning_failed: {e}"[:200])


def _after_practice(conn, a: dict, case: dict) -> None:
    s = get_settings()
    when = checker.retest_available_at(s.retest_delay_hours)
    gap = _current_gap(conn, case["id"])
    seen = _seen_question_ids(conn, case["student_id"])
    payload = {"gap_skill": gap["skill_id"], "delay_hours": s.retest_delay_hours}

    def schedule():
        sel = checker.select_retest(gap["skill_id"], seen)
        return {**sel, "available_at": when, "delay_hours": s.retest_delay_hours,
                "note": "Practice responses are recorded but not used to judge mastery."}

    sel = _run_agent(conn, case["id"], "Checker", "schedule_retest", payload, schedule)
    if not sel["ok"]:
        _set_stage(conn, case["id"], "teacher_review", sel["reason"])
        return
    _create_assessment(conn, case["id"], "retest", sel["question_ids"], available_at=when)
    _set_stage(conn, case["id"], "retest_pending")


def start_retest(case_id: int, early: bool = False) -> dict:
    with db.transaction() as conn:
        case = _get(conn, "cases", case_id)
        if case["stage"] != "retest_pending":
            raise WorkflowError("No retest is waiting for this case.")
        a = row_to_dict(conn.execute(
            "SELECT * FROM assessments WHERE case_id=? AND kind='retest' AND status='open' ORDER BY id DESC LIMIT 1",
            (case_id,)).fetchone())
        if a is None:
            raise WorkflowError("Retest not found.")
        if a["available_at"] > now_iso():
            if not early:
                raise WorkflowError(f"Retest unlocks at {a['available_at']} (UTC).")
            if not get_settings().allow_early_retest:
                raise WorkflowError("Early retest is disabled on this server (ALLOW_EARLY_RETEST=false).", 403)
            conn.execute("UPDATE assessments SET available_at=? WHERE id=?", (now_iso(), a["id"]))
            _log_skip(conn, case_id, "Checker", "early_retest_override",
                      f"Demo override: retest started before the scheduled time ({a['available_at']}).")
        _set_stage(conn, case_id, "retest")
        return case_detail(case_id, conn)


def _after_retest(conn, a: dict, case: dict) -> None:
    gap = _current_gap(conn, case["id"])
    responses = _enriched_responses(conn, a["id"])
    ver = conn.execute(
        "SELECT AVG(r.is_correct) FROM responses r JOIN assessments a ON a.id=r.assessment_id "
        "WHERE a.case_id=? AND a.kind='verification'", (case["id"],)).fetchone()[0]
    payload = {"gap": {k: gap[k] for k in ("id", "skill_id", "misconception", "status")}, "responses": responses,
               "verification_rate": ver}
    ev = _run_agent(conn, case["id"], "Checker", "evaluate_retest", payload,
                    lambda: checker.evaluate_retest(gap, responses, ver))
    _apply_mastery(conn, case["student_id"], checker.mastery_updates(
        responses, "retest", gap_skill=gap["skill_id"], retest_passed=ev["passed"]))
    evidence = gap["evidence"]
    evidence.setdefault("retests", []).append({"score": ev["score"], "passed": ev["passed"], "at": now_iso()})
    conn.execute("UPDATE gaps SET status=?, evidence=? WHERE id=?", (ev["new_gap_status"], dumps(evidence), gap["id"]))
    if ev["passed"]:
        conn.execute("UPDATE plans SET status='completed' WHERE case_id=? AND status='active'", (case["id"],))
        _set_stage(conn, case["id"], "completed", "gap_resolved")
    else:
        conn.execute("UPDATE gaps SET verified_by=COALESCE(verified_by,'Checker') WHERE id=?", (gap["id"],))
        _safe_plan_and_teach(conn, case)


# ======================================================================
# teacher actions (always logged with a reason)
# ======================================================================

def _log_override(conn, case_id, teacher, action, old, new, reason) -> None:
    conn.execute("INSERT INTO teacher_overrides (case_id, teacher_name, action, old_value, new_value, reason, "
                 "created_at) VALUES (?,?,?,?,?,?,?)", (case_id, teacher, action, old, new, reason, now_iso()))


def _validate_teacher_input(teacher: str, reason: str) -> tuple[str, str]:
    teacher, reason = (teacher or "").strip(), (reason or "").strip()
    if not 1 <= len(teacher) <= 60:
        raise WorkflowError("Teacher name is required (max 60 characters).", 400)
    if not 5 <= len(reason) <= 500:
        raise WorkflowError("Please give a reason (5-500 characters).", 400)
    return teacher, reason


def teacher_gap_decision(case_id: int, decision: str, teacher: str, reason: str,
                         focus_skill: Optional[str] = None) -> dict:
    teacher, reason = _validate_teacher_input(teacher, reason)
    if decision not in ("confirm", "reject"):
        raise WorkflowError("Decision must be 'confirm' or 'reject'.", 400)
    with db.transaction() as conn:
        case = _get(conn, "cases", case_id)
        gap = _current_gap(conn, case_id)
        if gap is None:
            raise WorkflowError("This case has no gap to review.")
        if case["stage"] in ("diagnostic", "verification"):
            raise WorkflowError("Wait until the Checker has finished verifying before overriding.")
        if focus_skill and focus_skill not in lessons():
            raise WorkflowError("Choose a focus skill that has lesson content.", 400)
        old = gap["status"]
        if decision == "confirm":
            focus = focus_skill or (gap["skill_id"] if gap["skill_id"] in lessons() else None)
            if focus is None:
                raise WorkflowError(f"'{skill_name(gap['skill_id'])}' has no lesson content yet. "
                                    "Choose a focus skill when confirming.", 400)
            conn.execute("UPDATE gaps SET status='confirmed', verified_by=?, verified_at=? WHERE id=?",
                         (f"teacher:{teacher}", now_iso(), gap["id"]))
            _log_override(conn, case_id, teacher, "confirm_gap", old, "confirmed", reason)
            _plan_and_teach(conn, case, created_by=f"teacher:{teacher}",
                            forced_focus=focus if (focus_skill or focus != gap["skill_id"]) else None)
        else:
            conn.execute("UPDATE gaps SET status='rejected', verified_by=?, verified_at=? WHERE id=?",
                         (f"teacher:{teacher}", now_iso(), gap["id"]))
            conn.execute("UPDATE plans SET status='cancelled' WHERE case_id=? AND status='active'", (case_id,))
            conn.execute("UPDATE assessments SET status='completed', completed_at=? WHERE case_id=? AND status='open'",
                         (now_iso(), case_id))
            _log_override(conn, case_id, teacher, "reject_gap", old, "rejected", reason)
            _set_stage(conn, case_id, "closed", "teacher_rejected_gap")
        return case_detail(case_id, conn)


def teacher_set_focus(case_id: int, focus_skill: str, teacher: str, reason: str) -> dict:
    teacher, reason = _validate_teacher_input(teacher, reason)
    if focus_skill not in lessons():
        raise WorkflowError("Choose a focus skill that has lesson content.", 400)
    with db.transaction() as conn:
        case = _get(conn, "cases", case_id)
        gap = _current_gap(conn, case_id)
        if gap is None or gap["status"] not in ("confirmed", "still_present"):
            raise WorkflowError("The focus can only be changed once a gap is verified. Confirm the gap first.")
        if case["stage"] not in ("learning", "retest_pending", "teacher_review"):
            raise WorkflowError(f"Can't change focus while the case is in stage '{case['stage']}'.")
        plan = _active_plan(conn, case_id)
        conn.execute("UPDATE assessments SET status='completed', completed_at=? "
                     "WHERE case_id=? AND kind='retest' AND status='open'", (now_iso(), case_id))
        _log_override(conn, case_id, teacher, "change_focus", plan["focus_skill"] if plan else None,
                      focus_skill, reason)
        _plan_and_teach(conn, case, created_by=f"teacher:{teacher}", forced_focus=focus_skill)
        return case_detail(case_id, conn)


def teacher_note(case_id: int, teacher: str, note: str) -> dict:
    teacher, note = _validate_teacher_input(teacher, note)
    with db.transaction() as conn:
        _get(conn, "cases", case_id)
        _log_override(conn, case_id, teacher, "note", None, None, note)
        return case_detail(case_id, conn)


# ======================================================================
# read models
# ======================================================================

STAGE_LABELS = {
    "diagnostic": "Answering the check-in questions",
    "verification": "Checker is verifying a suspected gap",
    "learning": "In the learning room",
    "retest_pending": "Waiting for the retest",
    "retest": "Retest in progress",
    "completed": "Gap closed",
    "closed": "Closed",
    "teacher_review": "Waiting for teacher review",
}


def case_detail(case_id: int, conn: Optional[sqlite3.Connection] = None) -> dict:
    if conn is None:
        with db.transaction() as c:
            return case_detail(case_id, c)
    case = _get(conn, "cases", case_id)
    assessments = [_assessment_view(conn, a) for a in rows_to_dicts(conn.execute(
        "SELECT * FROM assessments WHERE case_id=? ORDER BY id", (case_id,)).fetchall())]
    gap = _current_gap(conn, case_id)
    if gap:
        gap["skill_name"] = skill_name(gap["skill_id"])
    plan = _active_plan(conn, case_id) or row_to_dict(conn.execute(
        "SELECT * FROM plans WHERE case_id=? ORDER BY id DESC LIMIT 1", (case_id,)).fetchone())
    lesson = row_to_dict(conn.execute("SELECT * FROM lessons WHERE case_id=? ORDER BY id DESC LIMIT 1",
                                      (case_id,)).fetchone())
    runs = rows_to_dicts(conn.execute("SELECT * FROM agent_runs WHERE case_id=? ORDER BY id", (case_id,)).fetchall())
    overrides = rows_to_dicts(conn.execute("SELECT * FROM teacher_overrides WHERE case_id=? ORDER BY id",
                                           (case_id,)).fetchall())
    open_a = next((a for a in assessments if a["status"] == "open"), None)
    return {
        **case,
        "stage_label": STAGE_LABELS.get(case["stage"], case["stage"]),
        "assessments": assessments,
        "open_assessment": open_a,
        "gap": gap,
        "plan": plan,
        "lesson": lesson,
        "agent_runs": runs,
        "overrides": overrides,
    }


def student_overview(student_id: int) -> dict:
    with db.transaction() as conn:
        student = _get(conn, "students", student_id)
        cases = rows_to_dicts(conn.execute("SELECT * FROM cases WHERE student_id=? ORDER BY id DESC",
                                           (student_id,)).fetchall())
        active = next((c for c in cases if c["stage"] in ACTIVE_STAGES), None)
        mastery = rows_to_dicts(conn.execute("SELECT * FROM skill_mastery WHERE student_id=?",
                                             (student_id,)).fetchall())
        by_skill = {m["skill_id"]: m for m in mastery}
        skills = []
        for s in skills_by_id().values():
            m = by_skill.get(s["id"])
            skills.append({"skill_id": s["id"], "name": s["name"], "grade": s["grade"],
                           "status": m["status"] if m else "not_assessed",
                           "correct": m["correct"] if m else 0, "attempts": m["attempts"] if m else 0,
                           "updated_at": m["updated_at"] if m else None})
        resp = conn.execute(
            "SELECT a.kind, COUNT(*) n, SUM(r.is_correct) c FROM responses r JOIN assessments a "
            "ON a.id = r.assessment_id WHERE r.student_id=? GROUP BY a.kind", (student_id,)).fetchall()
        totals = {r["kind"]: {"attempted": r["n"], "correct": r["c"] or 0} for r in resp}
        assessments = rows_to_dicts(conn.execute(
            "SELECT a.id, a.case_id, a.kind, a.completed_at, COUNT(r.id) total, SUM(r.is_correct) correct "
            "FROM assessments a JOIN cases c ON c.id=a.case_id LEFT JOIN responses r ON r.assessment_id=a.id "
            "WHERE c.student_id=? AND a.status='completed' GROUP BY a.id ORDER BY a.completed_at DESC",
            (student_id,)).fetchall())
        assessments = [a for a in assessments if a["total"]]
        improvements = []
        for c in cases:
            rows = {r["kind"]: r for r in conn.execute(
                "SELECT a.kind, AVG(r.is_correct) rate, COUNT(r.id) n FROM responses r JOIN assessments a "
                "ON a.id=r.assessment_id WHERE a.case_id=? AND a.kind IN ('verification','retest') "
                "GROUP BY a.kind", (c["id"],)).fetchall()}
            if "verification" in rows and "retest" in rows:
                g = _current_gap(conn, c["id"])
                improvements.append({
                    "case_id": c["id"], "skill_name": skill_name(g["skill_id"]) if g else None,
                    "verification_rate": rows["verification"]["rate"], "retest_rate": rows["retest"]["rate"],
                    "change_points": round((rows["retest"]["rate"] - rows["verification"]["rate"]) * 100)})
        gaps = rows_to_dicts(conn.execute(
            "SELECT g.* FROM gaps g JOIN cases c ON c.id=g.case_id WHERE c.student_id=? ORDER BY g.id DESC",
            (student_id,)).fetchall())
        for g in gaps:
            g["skill_name"] = skill_name(g["skill_id"])
        history = rows_to_dicts(conn.execute(
            "SELECT r.created_at, r.question_id, r.answer_raw, r.is_correct, r.pattern, a.kind, a.case_id "
            "FROM responses r JOIN assessments a ON a.id=r.assessment_id WHERE r.student_id=? "
            "ORDER BY r.id DESC LIMIT 50", (student_id,)).fetchall())
        qs = questions()
        for h in history:
            h["prompt"] = render_prompt(qs[h["question_id"]])
        return {
            "student": student,
            "active_case": case_detail(active["id"], conn) if active else None,
            "cases": [{**c, "stage_label": STAGE_LABELS.get(c["stage"], c["stage"])} for c in cases],
            "skills": skills,
            "totals": totals,
            "assessments": assessments,
            "improvements": improvements,
            "gaps": gaps,
            "history": history,
            "recommended_next": _recommend(active, conn),
        }


def _recommend(active: Optional[dict], conn) -> dict:
    if active is None:
        return {"action": "start", "label": "Start a fractions check-in (5 questions)"}
    st = active["stage"]
    if st in ("diagnostic", "verification", "retest"):
        return {"action": "practice", "label": "Continue your questions"}
    if st == "learning":
        plan = _active_plan(conn, active["id"])
        return {"action": "learn", "label": f"Learning room: {skill_name(plan['focus_skill'])}" if plan else "Learning room"}
    if st == "retest_pending":
        a = conn.execute("SELECT available_at FROM assessments WHERE case_id=? AND kind='retest' AND status='open'",
                         (active["id"],)).fetchone()
        return {"action": "retest", "label": "Retest", "available_at": a["available_at"] if a else None}
    if st == "teacher_review":
        return {"action": "wait", "label": "Your teacher is reviewing your work"}
    return {"action": "start", "label": "Start a new check-in"}


def teacher_overview() -> list[dict]:
    with db.transaction() as conn:
        out = []
        for s in rows_to_dicts(conn.execute("SELECT * FROM students ORDER BY id").fetchall()):
            c = row_to_dict(conn.execute("SELECT * FROM cases WHERE student_id=? ORDER BY id DESC LIMIT 1",
                                         (s["id"],)).fetchone())
            gap = _current_gap(conn, c["id"]) if c else None
            tot = conn.execute("SELECT COUNT(*) n, SUM(is_correct) c FROM responses WHERE student_id=?",
                               (s["id"],)).fetchone()
            out.append({
                "student": s,
                "latest_case_id": c["id"] if c else None,
                "stage": c["stage"] if c else None,
                "stage_label": STAGE_LABELS.get(c["stage"], "") if c else "No activity yet",
                "gap_skill": skill_name(gap["skill_id"]) if gap else None,
                "gap_status": gap["status"] if gap else None,
                "confidence_label": gap["confidence_label"] if gap else None,
                "attempted": tot["n"], "correct": tot["c"] or 0,
                "needs_review": bool(c and c["stage"] == "teacher_review"),
            })
        return out
