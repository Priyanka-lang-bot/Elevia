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
from .content import curriculum, skill_name, skills_by_id, topic as topic_info, topics as all_topics
from .db import now_iso, row_to_dict
from .engine import check_answer
from .content import questions

router = APIRouter(prefix="/learn")

MIN_GRADE, MAX_GRADE = 3, 12
DEFAULT_TOPIC = orch.DEFAULT_TOPIC
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
    topic_id: str = Field(default=DEFAULT_TOPIC, max_length=40)


class AnswerBody(BaseModel):
    assessment_id: int
    question_id: str = Field(min_length=1, max_length=20)
    answer: str = Field(max_length=200)
    hints_used: int = Field(default=0, ge=0, le=5)


class PracticeFinishBody(BaseModel):
    assessment_id: int


class RetestBody(BaseModel):
    early: bool = False
    topic_id: str = Field(default=DEFAULT_TOPIC, max_length=40)


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

def _latest_case(conn, student_id: int, topic_id: str = DEFAULT_TOPIC) -> Optional[dict]:
    return row_to_dict(conn.execute(
        f"SELECT * FROM cases WHERE student_id = ? AND {orch._TOPIC_SQL} = ? ORDER BY id DESC LIMIT 1",
        (student_id, topic_id)).fetchone())


def _check_topic(topic_id: str) -> dict:
    try:
        return topic_info(topic_id)
    except KeyError:
        raise orch.NotFound("That topic is not available.")


def _skills_view(conn, student_id: int, topic_id: Optional[str] = None) -> list[dict]:
    mastery = {r["skill_id"]: r for r in conn.execute(
        "SELECT * FROM skill_mastery WHERE student_id = ?", (student_id,)).fetchall()}
    wanted = set(topic_info(topic_id)["skills"]) if topic_id else None
    out = []
    for s in skills_by_id().values():
        if wanted is not None and s["id"] not in wanted:
            continue
        m = mastery.get(s["id"])
        status = m["status"] if m else "not_assessed"
        out.append({"skill_id": s["id"], "name": s["name"], "grade": s["grade"], "status": status,
                    "label": MASTERY_LABELS[status], "correct": m["correct"] if m else 0,
                    "attempts": m["attempts"] if m else 0})
    return out


def _rounds_view(conn, student_id: int, topic_id: str = DEFAULT_TOPIC) -> list[dict]:
    out = []
    for c in orch.rows_to_dicts(conn.execute(
            f"SELECT * FROM cases WHERE student_id = ? AND {orch._TOPIC_SQL} = ? ORDER BY id DESC LIMIT 10",
            (student_id, topic_id)).fetchall()):
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


def _topic_brief(tid: str) -> dict:
    t = topic_info(tid)
    sub = next(s for s in curriculum()["subjects"] if s["id"] == t["subject"])
    return {"id": tid, "name": t["name"], "subject": sub["name"], "subject_id": sub["id"], "color": sub["color"],
            "icon": sub["icon"], "objectives": t["objectives"], "description": t["description"]}


def build_state(conn, student: dict, topic_id: str = DEFAULT_TOPIC) -> dict:
    case = _latest_case(conn, student["id"], topic_id)
    tname = topic_info(topic_id)["name"]
    base = {"student": {"name": student["display_name"], "grade": student["grade"]},
            "topic": _topic_brief(topic_id),
            "skills": _skills_view(conn, student["id"], topic_id), "rounds": _rounds_view(conn, student["id"], topic_id),
            "settings": {"retest_delay_hours": get_settings().retest_delay_hours}}
    if case is None:
        return {**base, "phase": "start", "journey": [{"key": k, "label": l, "status": "todo"} for k, l in STEPS],
                "headline": f"Ready for a {tname.lower()} check-in?",
                "why": f"Five short questions show which {tname.lower()} skills are strong and which need practice.",
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
                   headline="Check-in", why=f"These {n} questions show ELEVIA which {tname.lower()} skills are strong and "
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


def _state_for(conn, user: dict, topic_id: str = DEFAULT_TOPIC) -> dict:
    student = _linked_student(conn, user)
    if student is None:
        profile_grade = _profile_grade(conn, user)
        return {"phase": "welcome", "student": {"name": _first_name(user["full_name"]), "grade": profile_grade},
                "needs_grade": profile_grade is None, "grades": list(range(MIN_GRADE, MAX_GRADE + 1)),
                "journey": [{"key": k, "label": l, "status": "todo"} for k, l in STEPS],
                "headline": f"Welcome, {_first_name(user['full_name'])}!",
                "why": "Pick a topic. ELEVIA starts with a short check-in, finds out what to practise, checks that "
                       "carefully, teaches it, and retests you.",
                "topic": _topic_brief(topic_id),
                "skills": [], "rounds": [], "next_action": {"kind": "start", "label": "Start the check-in"}}
    return build_state(conn, student, topic_id)


# ---------------------------------------------------------------- routes

# ---------------------------------------------------------------- dashboard (all subjects, few queries)

PHASE_OF_STAGE = {"diagnostic": "checkin", "verification": "verify", "learning": "learn",
                  "retest_pending": "retest_wait", "retest": "retest", "teacher_review": "teacher_wait"}
PHASE_LABEL = {"not_started": "Not started", "checkin": "Check-in in progress", "verify": "Double-check in progress",
               "learn": "Lesson ready", "retest_wait": "Retest scheduled", "retest": "Retest in progress",
               "teacher_wait": "Waiting for your teacher", "done": "Finished"}
NEXT_LABEL = {"not_started": "Start the check-in", "checkin": "Continue the check-in", "verify": "Answer the double-check",
              "learn": "Open your lesson", "retest_wait": "See your retest", "retest": "Continue your retest",
              "teacher_wait": "See status", "done": "Start a new check-in"}


def build_dashboard(conn, user: dict) -> dict:
    student = _linked_student(conn, user)
    cur = curriculum()
    profile_grade = None if student else _profile_grade(conn, user)
    grade = student["grade"] if student else profile_grade
    out = {"student": {"name": student["display_name"] if student else _first_name(user["full_name"]), "grade": grade},
           "needs_grade": student is None and profile_grade is None, "grades": list(range(MIN_GRADE, MAX_GRADE + 1)),
           "settings": {"retest_delay_hours": get_settings().retest_delay_hours}}
    cases, gaps, retests, mastery, answers = [], {}, {}, {}, {"total": 0, "correct": 0}
    if student:
        cases = orch.rows_to_dicts(conn.execute(
            f"SELECT cases.*, {orch._TOPIC_SQL} AS topic_id FROM cases WHERE student_id = ? ORDER BY id",
            (student["id"],)).fetchall())
        ids = [c["id"] for c in cases] or [0]
        marks = ",".join("?" * len(ids))
        for g in orch.rows_to_dicts(conn.execute(f"SELECT * FROM gaps WHERE case_id IN ({marks}) ORDER BY id", ids).fetchall()):
            gaps[g["case_id"]] = g                      # latest gap per case
        for a in orch.rows_to_dicts(conn.execute(
                f"SELECT * FROM assessments WHERE case_id IN ({marks}) AND kind='retest' AND status='open'", ids).fetchall()):
            retests[a["case_id"]] = a
        mastery = {r["skill_id"]: dict(r) for r in conn.execute(
            "SELECT * FROM skill_mastery WHERE student_id = ?", (student["id"],)).fetchall()}
        row = conn.execute(
            f"SELECT COUNT(*) AS n, COALESCE(SUM(r.is_correct),0) AS c FROM responses r JOIN assessments a "
            f"ON a.id = r.assessment_id WHERE a.case_id IN ({marks}) AND a.kind != 'practice'", ids).fetchone()
        answers = {"total": row["n"], "correct": row["c"]}
    latest = {}
    for c in cases:
        latest[c["topic_id"]] = c
    now = now_iso()
    subjects, cont, upcoming, open_gaps = [], [], [], []
    for sub in cur["subjects"]:
        tlist = []
        for tid in sub["topics"]:
            t = cur["topics"][tid]
            c = latest.get(tid)
            phase = "not_started" if c is None else ("done" if c["stage"] in ("completed", "closed")
                                                       else PHASE_OF_STAGE.get(c["stage"], "checkin"))
            g = gaps.get(c["id"]) if c else None
            sk = [mastery.get(x, {}).get("status", "not_assessed") for x in t["skills"]]
            item = {"id": tid, "name": t["name"], "unit": t["unit"], "description": t["description"],
                    "objectives": t["objectives"], "grade_min": t["grade_min"], "grade_max": t["grade_max"],
                    "recommended": grade is not None and t["grade_min"] <= grade <= t["grade_max"],
                    "phase": phase, "phase_label": PHASE_LABEL[phase], "next_label": NEXT_LABEL[phase],
                    "outcome": OUTCOMES.get(c["closed_reason"], ("Finished",))[0] if phase == "done" else None,
                    "skills_total": len(sk), "skills_mastered": sk.count("mastered"),
                    "skills_checked": sum(1 for x in sk if x != "not_assessed"),
                    "rounds": sum(1 for x in cases if x["topic_id"] == tid)}
            tlist.append(item)
            if phase not in ("not_started", "done"):
                cont.append({"topic_id": tid, "topic": t["name"], "subject": sub["name"], "color": sub["color"],
                             "phase": phase, "phase_label": PHASE_LABEL[phase], "next_label": NEXT_LABEL[phase],
                             "skill": skill_name(g["skill_id"]) if g else None})
            if c and c["id"] in retests and phase == "retest_wait":
                avail = retests[c["id"]]["available_at"]
                upcoming.append({"topic_id": tid, "topic": t["name"], "skill": skill_name(g["skill_id"]) if g else None,
                                 "available_at": avail, "unlocked": not avail or avail <= now})
            if g and g["status"] in ("suspected", "confirmed", "inconclusive", "still_present") and phase != "done":
                gv = _gap_view(g, c["stage"])
                open_gaps.append({"topic_id": tid, "topic": t["name"], "skill": gv.get("skill"), "state": gv["state"],
                                  "headline": gv["headline"]})
        subjects.append({"id": sub["id"], "name": sub["name"], "icon": sub["icon"], "color": sub["color"],
                         "description": sub["description"], "topics": tlist, "planned": sub.get("planned", [])})
    history = []
    for c in reversed(cases[-12:]):
        g = gaps.get(c["id"])
        done = c["stage"] in ("completed", "closed")
        history.append({"topic_id": c["topic_id"], "topic": cur["topics"].get(c["topic_id"], {}).get("name", c["topic_id"]),
                        "date": c["created_at"], "skill": skill_name(g["skill_id"]) if g else None,
                        "outcome": OUTCOMES.get(c["closed_reason"], ("Finished",))[0] if done
                        else PHASE_LABEL.get(PHASE_OF_STAGE.get(c["stage"], ""), "In progress")})
    counts = {k: 0 for k in MASTERY_LABELS}
    for m in mastery.values():
        counts[m["status"]] = counts.get(m["status"], 0) + 1
    recommended = [t for s in subjects for t in s["topics"] if t["recommended"] and t["phase"] == "not_started"][:4]
    out.update(phase="dashboard" if student else "welcome", subjects=subjects, continue_learning=cont,
               upcoming_retests=upcoming, open_gaps=open_gaps, history=history,
               mastery_counts={MASTERY_LABELS[k]: v for k, v in counts.items() if k != "not_assessed"},
               answers=answers, recommended=[{"id": t["id"], "name": t["name"]} for t in recommended],
               totals={"topics_started": len(latest), "topics_available": len(cur["topics"]),
                       "skills_mastered": counts.get("mastered", 0)})
    return out


# ---------------------------------------------------------------- routes

@router.get("/curriculum")
def curriculum_view(user: dict = Depends(learner)):
    return {"subjects": curriculum()["subjects"],
            "topics": {k: {x: v[x] for x in ("name", "subject", "unit", "grade_min", "grade_max", "description",
                                              "objectives")} for k, v in all_topics().items()}}


@router.get("/state")
def state(topic: str = DEFAULT_TOPIC, user: dict = Depends(learner)):
    _check_topic(topic)
    with db.transaction() as conn:
        return _state_for(conn, user, topic)


@router.get("/dashboard")
def dashboard(user: dict = Depends(learner)):
    with db.transaction() as conn:
        return build_dashboard(conn, user)


@router.post("/start")
def start(body: StartBody, user: dict = Depends(learner)):
    """Begin (or continue) a topic. Safe to call twice: an unfinished round is returned, not duplicated."""
    _check_topic(body.topic_id)
    with db.transaction() as conn:
        student = _ensure_student(conn, user, body.grade)
    orch.start_case(student["id"], body.topic_id)  # reuses the active case on this topic, or starts the next one
    with db.transaction() as conn:
        return _state_for(conn, user, body.topic_id)


@router.post("/answer")
def answer(body: AnswerBody, user: dict = Depends(learner)):
    with db.transaction() as conn:
        student = _linked_student(conn, user)
        if student is None:
            raise orch.WorkflowError("Start the check-in first.")
        a, case = _own_assessment(conn, student, body.assessment_id)
        tid = orch.case_topic(conn, case["id"])
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
                        "state": _state_for(conn, user, tid)}
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
                "assessment_completed": fb["assessment_completed"], "state": _state_for(conn, user, tid)}


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
        a, case = _own_assessment(conn, student, body.assessment_id)
        tid = orch.case_topic(conn, case["id"])
        already = a["kind"] == "practice" and a["status"] == "completed"
    if not already:
        orch.finish_practice(body.assessment_id)
    with db.transaction() as conn:
        return _state_for(conn, user, tid)


@router.post("/retest/start")
def start_retest(body: RetestBody, user: dict = Depends(learner)):
    _check_topic(body.topic_id)
    with db.transaction() as conn:
        student = _linked_student(conn, user)
        case = _latest_case(conn, student["id"], body.topic_id) if student else None
        if case is None:
            raise orch.WorkflowError("There is no retest waiting.")
        stage = case["stage"]
    if stage == "retest":  # already started (double click): just show it
        with db.transaction() as conn:
            return _state_for(conn, user, body.topic_id)
    orch.start_retest(case["id"], early=body.early)
    with db.transaction() as conn:
        return _state_for(conn, user, body.topic_id)
