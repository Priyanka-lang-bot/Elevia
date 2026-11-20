"""Student learning journey for logged-in students and independent learners.

This is a thin, authenticated layer over the existing orchestrator (backend/orchestrator.py).
It adds three things and nothing else:

  1. Identity: a logged-in account is linked to one row in `students` (table `learner_links`),
     and every route checks that the case/assessment it touches belongs to that student.
  2. A student-facing view model: where you are, what you are being tested on, why, whether a
     suspected gap has been verified, what to do next. No agent internals, codes or confidence numbers.
  3. Idempotent actions: a double-click or a second tab cannot record an answer twice or break the state.

All decisions (diagnosis, verification, planning, grading, mastery) are still made by the rule-based
agents through the orchestrator; nothing here grades or decides.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from . import db, orchestrator as orch
from .accounts.routes import active_user
from .accounts.errors import AccountError
from .config import get_settings
from .content import skill_name, skills_by_id
from .db import now_iso, row_to_dict
from .engine import check_answer
from .content import questions

router = APIRouter(prefix="/learn")

MIN_GRADE, MAX_GRADE = 3, 8
DEFAULT_GRADE = 5

STEPS = [("checkin", "Check-in"), ("verify", "Double-check"), ("learn", "Learn & practise"),
         ("retest", "Retest"), ("result", "Result")]

MASTERY_LABELS = {"not_assessed": "Not checked yet", "needs_practice": "Needs practice",
                  "developing": "Getting there", "mastered": "Mastered"}

OUTCOMES = {
    "gap_resolved": ("Gap closed", "good",
                     "You passed the retest on new questions. That skill is now marked as mastered."),
    "no_gap_found": ("No gap found", "good",
                     "You answered everything correctly, so there is nothing to fix right now."),
    "gap_not_supported": ("It was a slip, not a gap", "good",
                          "ELEVIA double-checked with new questions and your earlier mistake did not come back. "
                          "Nothing needs fixing, and your plan was not changed."),
    "teacher_rejected_gap": ("Your teacher reviewed this", "good",
                             "Your teacher decided no extra lesson is needed for this one."),
}


# ---------------------------------------------------------------- request bodies

class StartBody(BaseModel):
    grade: Optional[int] = Field(default=None, ge=MIN_GRADE, le=MAX_GRADE)


class AnswerBody(BaseModel):
    assessment_id: int
    question_id: str = Field(min_length=1, max_length=20)
    answer: str = Field(max_length=40)
    hints_used: int = Field(default=0, ge=0, le=5)


class PracticeFinishBody(BaseModel):
    assessment_id: int


class RetestBody(BaseModel):
    early: bool = False


# ---------------------------------------------------------------- identity

def learner(user: dict = Depends(active_user)) -> dict:
    if user["role"] not in ("student", "learner"):
        raise AccountError("The learning area is for students and independent learners.", 403)
    return user


def _first_name(full_name: str) -> str:
    return (full_name.strip().split() or ["Student"])[0][:40]


def _linked_student(conn, user: dict) -> Optional[dict]:
    return row_to_dict(conn.execute(
        "SELECT s.* FROM learner_links l JOIN students s ON s.id = l.student_id WHERE l.user_id = ?",
        (user["id"],)).fetchone())


def _profile_grade(conn, user: dict) -> Optional[int]:
    row = conn.execute("SELECT grade FROM student_profiles WHERE user_id = ?", (user["id"],)).fetchone()
    g = row["grade"] if row else None
    return g if g is not None and MIN_GRADE <= g <= MAX_GRADE else None


def _ensure_student(conn, user: dict, grade: Optional[int]) -> dict:
    student = _linked_student(conn, user)
    if student:
        return student
    grade = _profile_grade(conn, user) or grade
    if grade is None:
        raise orch.WorkflowError("Please choose your grade to begin.", 400)
    cur = conn.execute("INSERT INTO students (display_name, grade, is_sample, created_at) VALUES (?,?,?,?)",
                       (_first_name(user["full_name"]), int(grade), 0, now_iso()))
    conn.execute("INSERT INTO learner_links (user_id, student_id, created_at) VALUES (?,?,?)",
                 (user["id"], cur.lastrowid, now_iso()))
    return orch._get(conn, "students", cur.lastrowid)


def _own_case(conn, student: dict, case_id: int) -> dict:
    case = orch._get(conn, "cases", case_id)
    if case["student_id"] != student["id"]:
        raise orch.NotFound(f"Case {case_id} not found")
    return case


def _own_assessment(conn, student: dict, assessment_id: int) -> tuple[dict, dict]:
    a = orch._get(conn, "assessments", assessment_id)
    return a, _own_case(conn, student, a["case_id"])


# ---------------------------------------------------------------- view model (student wording only)

def _latest_case(conn, student_id: int) -> Optional[dict]:
    return row_to_dict(conn.execute("SELECT * FROM cases WHERE student_id = ? ORDER BY id DESC LIMIT 1",
                                    (student_id,)).fetchone())


def _skills_view(conn, student_id: int) -> list[dict]:
    mastery = {r["skill_id"]: r for r in conn.execute(
        "SELECT * FROM skill_mastery WHERE student_id = ?", (student_id,)).fetchall()}
    out = []
    for s in skills_by_id().values():
        m = mastery.get(s["id"])
        status = m["status"] if m else "not_assessed"
        out.append({"skill_id": s["id"], "name": s["name"], "grade": s["grade"], "status": status,
                    "label": MASTERY_LABELS[status], "correct": m["correct"] if m else 0,
                    "attempts": m["attempts"] if m else 0})
    return out


def _rounds_view(conn, student_id: int) -> list[dict]:
    out = []
    for c in orch.rows_to_dicts(conn.execute(
            "SELECT * FROM cases WHERE student_id = ? ORDER BY id DESC LIMIT 10", (student_id,)).fetchall()):
        gap = orch._current_gap(conn, c["id"])
        if c["stage"] in ("completed", "closed"):
            label = OUTCOMES.get(c["closed_reason"], ("Finished", "good", ""))[0]
        else:
            label = "In progress"
        out.append({"case_id": c["id"], "date": c["created_at"], "outcome": label,
                    "skill": skill_name(gap["skill_id"]) if gap else None})
    return out


def _gap_view(gap: Optional[dict], stage: str) -> dict:
    """Whether the suspected gap has been verified, in plain words."""
    if gap is None:
        return {"state": "none", "headline": "No gap suspected",
                "text": "ELEVIA has not found anything it needs to check."}
    name = skill_name(gap["skill_id"])
    st = gap["status"]
    if st == "suspected":
        return {"state": "checking", "skill": name, "headline": "Possible gap: not confirmed yet",
                "text": f"ELEVIA noticed a pattern in your answers about {name.lower()}. It could be a real gap or "
                        "just a slip, so nothing changes until two new questions have checked it."}
    if st == "confirmed":
        by = gap.get("verified_by") or ""
        who = "your teacher" if by.startswith("teacher:") else "the double-check questions"
        return {"state": "verified", "skill": name, "headline": "Gap confirmed",
                "text": f"{who.capitalize()} showed the same kind of mistake again, so {name.lower()} is the "
                        "next thing to practise."}
    if st == "rejected":
        return {"state": "not_supported", "skill": name, "headline": "Not a real gap",
                "text": f"The new questions did not show the same mistake, so {name.lower()} is not being treated "
                        "as a gap."}
    if st == "inconclusive":
        return {"state": "unclear", "skill": name, "headline": "Not clear yet",
                "text": "The results were mixed, so ELEVIA will not guess. Your teacher will look at your answers."}
    if st == "resolved":
        return {"state": "resolved", "skill": name, "headline": "Gap closed",
                "text": f"You passed the retest, so {name.lower()} is now marked as mastered."}
    return {"state": "still_present", "skill": name, "headline": "Still needs practice",
            "text": f"The retest was not passed yet, so {name.lower()} stays open. A fresh lesson is ready."}


def _step_statuses(stage: str, assessments: list[dict], lesson: Optional[dict], terminal: bool) -> list[dict]:
    done = {k: any(a["kind"] == kind and a["status"] == "completed" for a in assessments)
            for k, kind in (("checkin", "diagnostic"), ("verify", "verification"),
                            ("learn", "practice"), ("retest", "retest"))}
    # which step is the student on right now?
    current = {"diagnostic": "checkin", "verification": "verify", "learning": "learn",
               "retest_pending": "retest", "retest": "retest"}.get(stage)
    if stage == "teacher_review":
        current = "verify" if not lesson else "learn"
    # a replanned case (failed retest) puts the student back at "learn"
    steps = []
    for key, label in STEPS:
        if key == "result":
            status = "done" if terminal else "todo"
        elif key == current:
            status = "current"
        elif done[key]:
            status = "done"
        elif terminal or stage == "teacher_review":
            status = "skipped"
        else:
            status = "todo"
        steps.append({"key": key, "label": label, "status": status})
    return steps


def _retest_info(case: dict, retest: Optional[dict]) -> Optional[dict]:
    if not retest:
        return None
    s = get_settings()
    avail = retest["available_at"]
    now = now_iso()
    unlocked = not avail or avail <= now
    seconds = 0
    if not unlocked:
        try:
            seconds = max(0, int((datetime.fromisoformat(avail) - datetime.now(timezone.utc)).total_seconds()))
        except ValueError:
            seconds = 0
    return {"available_at": avail, "unlocked": unlocked, "seconds_left": seconds,
            "delay_hours": s.retest_delay_hours, "can_start_early": bool(s.allow_early_retest and not unlocked)}


def _assessment_for_student(a: dict) -> dict:
    return {"id": a["id"], "kind": a["kind"], "total": a["total"], "answered": a["answered"],
            "questions": [{k: v for k, v in q.items() if k not in ("skill_id", "type")} for q in a["questions"]]}


def _lesson_view(lesson_row: Optional[dict]) -> Optional[dict]:
    if not lesson_row:
        return None
    c = lesson_row["content"]
    return {"title": c["title"], "skill_name": c["skill_name"], "big_idea": c["big_idea"],
            "personal_note": c["personal_note"], "steps": c["steps"], "sense_check": c["sense_check"],
            "worked_examples": c["worked_examples"],
            "practice_note": "Practice answers give you feedback, but they do not change your progress. "
                             "The retest does."}


def _why_learning(plan: Optional[dict], gap: Optional[dict]) -> Optional[str]:
    if not plan:
        return None
    focus = skill_name(plan["focus_skill"])
    path = (plan["path"] or {}).get("path", [])
    if plan["created_by"].startswith("teacher:"):
        return f"Your teacher chose {focus} as your next focus."
    gap_skill = skill_name(gap["skill_id"]) if gap else focus
    if gap and plan["focus_skill"] != gap["skill_id"]:
        return (f"The double-check confirmed a gap in {gap_skill.lower()}. You will start with {focus.lower()}, "
                "an earlier skill that also showed mistakes, because it builds up to it.")
    still = gap and gap["status"] == "still_present"
    return (f"{'The retest showed' if still else 'The double-check confirmed'} that {focus.lower()} needs more "
            "practice, so that is the focus now.")


def build_state(conn, student: dict, *, name: Optional[str] = None) -> dict:
    case = _latest_case(conn, student["id"])
    base = {"student": {"name": student["display_name"], "grade": student["grade"]},
            "skills": _skills_view(conn, student["id"]), "rounds": _rounds_view(conn, student["id"]),
            "settings": {"retest_delay_hours": get_settings().retest_delay_hours}}
    if case is None:
        return {**base, "phase": "start", "journey": [{"key": k, "label": l, "status": "todo"} for k, l in STEPS],
                "headline": f"Hi {student['display_name']}! Ready for a fractions check-in?",
                "why": "Five short questions show which fraction skills are strong and which need practice.",
                "next_action": {"kind": "start", "label": "Start the check-in"}}

    d = orch.case_detail(case["id"], conn)
    stage, gap, plan = d["stage"], d["gap"], d["plan"]
    assessments = d["assessments"]
    terminal = stage in ("completed", "closed")
    open_a = d["open_assessment"]
    retest_a = next((a for a in reversed(assessments) if a["kind"] == "retest" and a["status"] == "open"), None)
    retests = ((gap or {}).get("evidence") or {}).get("retests", [])
    last_retest = retests[-1] if retests else None
    out = {**base, "case_id": d["id"], "round": len(retests) + 1, "journey": _step_statuses(stage, assessments, d["lesson"], terminal),
           "gap": _gap_view(gap, stage), "stage": stage}

    if stage == "diagnostic" and open_a:
        n = open_a["total"]
        skills = sorted({q["skill_name"] for q in open_a["questions"]})
        out.update(phase="checkin", assessment=_assessment_for_student(open_a), testing_on=skills,
                   headline="Check-in", why=f"These {n} questions show ELEVIA which fraction skills are strong and "
                                            "which need practice. Do your best; wrong answers help ELEVIA help you.",
                   next_action={"kind": "answer", "label": "Answer the questions"})
    elif stage == "verification" and open_a:
        out.update(phase="verify", assessment=_assessment_for_student(open_a),
                   testing_on=[skill_name(gap["skill_id"])] if gap else [],
                   headline="Double-check",
                   why="Some of your answers followed a pattern. These new questions check whether it is a real gap "
                       "or just a slip. ELEVIA will not teach anything until it has checked.",
                   next_action={"kind": "answer", "label": "Answer the 2 new questions"})
    elif stage == "learning":
        practice = next((a for a in reversed(assessments) if a["kind"] == "practice" and a["status"] == "open"), None)
        out.update(phase="learn", lesson=_lesson_view(d["lesson"]), why_learning=_why_learning(plan, gap),
                   assessment=_assessment_for_student(practice) if practice else None,
                   testing_on=[skill_name(plan["focus_skill"])] if plan else [],
                   previous_retest=last_retest,
                   headline=f"Learn: {skill_name(plan['focus_skill'])}" if plan else "Learn",
                   why="Read the lesson, then try the practice questions. Hints and full solutions are available "
                       "here. Practice does not change your progress; the retest does.",
                   next_action={"kind": "learn", "label": "Read the lesson, then practise"})
    elif stage == "retest_pending":
        info = _retest_info(d, retest_a)
        out.update(phase="retest_wait", retest=info, testing_on=[skill_name(gap["skill_id"])] if gap else [],
                   headline="Retest coming up",
                   why="A short break helps. The retest uses 3 brand-new questions and shows whether you really "
                       "learned it, not just remembered the practice. You pass with 2 out of 3.",
                   next_action={"kind": "wait_retest", "label": "Come back for your retest"})
    elif stage == "retest" and open_a:
        out.update(phase="retest", assessment=_assessment_for_student(open_a),
                   testing_on=[skill_name(gap["skill_id"])] if gap else [],
                   headline="Retest",
                   why="Three new questions. Get at least 2 right to close this gap.",
                   next_action={"kind": "answer", "label": "Answer the 3 retest questions"})
    elif stage == "teacher_review":
        reason = d["closed_reason"] or ""
        if reason.startswith("processing_failed"):
            text = ("Something went wrong on our side while checking your answers. Your answers are saved. "
                    "Your teacher can pick this up.")
        elif reason == "verification_inconclusive":
            text = ("Your double-check answers were mixed, so ELEVIA will not guess. "
                    "Your teacher will look at them and decide what to practise.")
        else:
            text = "ELEVIA needs your teacher to look at this before going further. Your answers are saved."
        out.update(phase="teacher_wait", headline="Waiting for your teacher", why=text,
                   next_action={"kind": "wait_teacher", "label": "Your teacher will review this"})
    else:  # completed / closed
        title, tone, text = OUTCOMES.get(d["closed_reason"], ("Finished", "good", "This round is finished."))
        out.update(phase="done", outcome={"title": title, "tone": tone, "text": text,
                                          "retest": last_retest if d["closed_reason"] == "gap_resolved" else None},
                   headline=title, why=text,
                   next_action={"kind": "new_checkin", "label": "Start a new check-in"})
    return out


def _state_for(conn, user: dict) -> dict:
    student = _linked_student(conn, user)
    if student is None:
        profile_grade = _profile_grade(conn, user)
        return {"phase": "welcome", "student": {"name": _first_name(user["full_name"]), "grade": profile_grade},
                "needs_grade": profile_grade is None, "grades": list(range(MIN_GRADE, MAX_GRADE + 1)),
                "journey": [{"key": k, "label": l, "status": "todo"} for k, l in STEPS],
                "headline": f"Welcome, {_first_name(user['full_name'])}!",
                "why": "ELEVIA starts with a short fractions check-in, finds out what to practise, checks that "
                       "carefully, teaches it, and retests you.",
                "skills": [], "rounds": [], "next_action": {"kind": "start", "label": "Start the check-in"}}
    return build_state(conn, student)


# ---------------------------------------------------------------- routes

@router.get("/state")
def state(user: dict = Depends(learner)):
    with db.transaction() as conn:
        return _state_for(conn, user)


@router.post("/start")
def start(body: StartBody, user: dict = Depends(learner)):
    """Begin (or continue) the journey. Safe to call twice: an unfinished round is returned, not duplicated."""
    with db.transaction() as conn:
        student = _ensure_student(conn, user, body.grade)
    orch.start_case(student["id"])  # reuses an active case; otherwise creates the next diagnostic
    with db.transaction() as conn:
        return _state_for(conn, user)


@router.post("/answer")
def answer(body: AnswerBody, user: dict = Depends(learner)):
    with db.transaction() as conn:
        student = _linked_student(conn, user)
        if student is None:
            raise orch.WorkflowError("Start the check-in first.")
        a, case = _own_assessment(conn, student, body.assessment_id)
        q = questions().get(body.question_id)
        if q is None or body.question_id not in a["question_ids"]:
            raise orch.WorkflowError("That question is not part of this set.", 400)
        prior = row_to_dict(conn.execute("SELECT * FROM responses WHERE assessment_id=? AND question_id=?",
                                         (a["id"], body.question_id)).fetchone())
    if prior:
        # Double-click / second tab / retry after a lost response: same answer = same result, recorded once.
        same = check_answer(q, body.answer)
        if same.valid and same.normalized == check_answer(q, prior["answer_raw"]).normalized:
            with db.transaction() as conn:
                return {"accepted": True, "duplicate": True, "is_correct": bool(prior["is_correct"]),
                        "state": _state_for(conn, user)}
        raise orch.WorkflowError("You have already answered this question.")

    fb = orch.submit_answer(body.assessment_id, body.question_id, body.answer, body.hints_used)
    if not fb.get("accepted"):
        return {"accepted": False, "error": fb.get("error") or "Please check your answer."}
    feedback = {"is_correct": fb["is_correct"], "notes": fb.get("notes", [])}
    if "message" in fb:
        feedback["message"] = fb["message"]
    if "expected" in fb:  # practice only
        feedback["expected"] = fb["expected"]
        feedback["solution"] = fb.get("solution")
    with db.transaction() as conn:
        return {"accepted": True, "duplicate": False, "feedback": feedback,
                "assessment_completed": fb["assessment_completed"], "state": _state_for(conn, user)}


@router.get("/hint")
def hint(assessment_id: int, question_id: str, level: int = 1, user: dict = Depends(learner)):
    with db.transaction() as conn:
        student = _linked_student(conn, user)
        if student is None:
            raise orch.WorkflowError("Start the check-in first.")
        _own_assessment(conn, student, assessment_id)
    h = orch.get_hint(assessment_id, question_id, level)
    return {"level": h["level"], "total": h["total"], "hint": h["hint"]}


@router.post("/practice/finish")
def finish_practice(body: PracticeFinishBody, user: dict = Depends(learner)):
    with db.transaction() as conn:
        student = _linked_student(conn, user)
        if student is None:
            raise orch.WorkflowError("Start the check-in first.")
        a, _ = _own_assessment(conn, student, body.assessment_id)
        already = a["kind"] == "practice" and a["status"] == "completed"
    if not already:
        orch.finish_practice(body.assessment_id)
    with db.transaction() as conn:
        return _state_for(conn, user)


@router.post("/retest/start")
def start_retest(body: RetestBody, user: dict = Depends(learner)):
    with db.transaction() as conn:
        student = _linked_student(conn, user)
        case = _latest_case(conn, student["id"]) if student else None
        if case is None:
            raise orch.WorkflowError("There is no retest waiting.")
        stage = case["stage"]
    if stage == "retest":  # already started (double click): just show it
        with db.transaction() as conn:
            return _state_for(conn, user)
    orch.start_retest(case["id"], early=body.early)
    with db.transaction() as conn:
        return _state_for(conn, user)
