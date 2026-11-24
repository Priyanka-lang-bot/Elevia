"""Learning progress for the people allowed to see it: teachers (their classes), parents (their linked children,
if the child's consent includes progress) and anyone a learner has shared with.

Every read goes through accounts.permissions (which also writes the access log). Only a teacher of the
student's class can review a gap or change the learning focus; those actions reuse the orchestrator's
audited override functions, so every decision is logged with a reason.
"""
from __future__ import annotations

from collections import Counter
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from . import db, history, orchestrator as orch
from .accounts import permissions
from .accounts.errors import AccountError
from .accounts.routes import active_user
from .content import lessons, misconceptions, skill_name, skills_by_id, topics
from .db import now_iso, row_to_dict, rows_to_dicts

router = APIRouter(prefix="/progress")

MASTERY = {"not_assessed": "Not checked", "needs_practice": "Needs practice", "developing": "Developing",
           "mastered": "Mastered"}
GAP_STATUS = {"suspected": "Suspected (being checked)", "confirmed": "Confirmed by the double-check",
              "rejected": "Not supported (a slip)", "inconclusive": "Inconclusive: needs a teacher",
              "resolved": "Closed: retest passed", "still_present": "Still open: retest not passed"}
REVIEW_REASON = {"verification_inconclusive": "Double-check was mixed: confirm or reject the gap",
                 "no_new_questions": "Ran out of new questions for this skill",
                 "no_lesson_available": "No lesson exists for this gap yet"}


def _review_reason(code: Optional[str]) -> str:
    code = code or ""
    if code in REVIEW_REASON:
        return REVIEW_REASON[code]
    if code.startswith("processing_failed"):
        return "Something went wrong while checking answers (answers were kept)"
    if code.startswith("planning_failed"):
        return "The Planner couldn't make a plan for this gap"
    return code or "Needs a teacher's decision"


VIEWER_ROLES = ("teacher", "parent", "learner", "student", "school_admin")


class Decision(BaseModel):
    decision: str = Field(pattern="^(confirm|reject)$")
    reason: str = Field(min_length=5, max_length=500)
    focus_skill: Optional[str] = Field(default=None, max_length=60)


class Focus(BaseModel):
    focus_skill: str = Field(max_length=60)
    reason: str = Field(min_length=5, max_length=500)


class Note(BaseModel):
    note: str = Field(min_length=5, max_length=500)


# ---------------------------------------------------------------- who can I see?

def _candidates(conn, user: dict) -> list[dict]:
    """People whose progress this viewer might see, with a group label. Permission is checked afterwards."""
    return _role_candidates(conn, user) + rows_to_dicts(conn.execute(
        "SELECT u.id, u.full_name, NULL AS class_id, 'Shared with you' AS grp FROM share_grants g "
        "JOIN users u ON u.id = g.owner_user_id WHERE g.grantee_user_id = ? AND g.status = 'active' "
        "AND (g.expires_at IS NULL OR g.expires_at > ?) ORDER BY u.full_name", (user["id"], now_iso())).fetchall())


def _role_candidates(conn, user: dict) -> list[dict]:
    role, uid = user["role"], user["id"]
    if role == "teacher":
        return rows_to_dicts(conn.execute(
            "SELECT DISTINCT u.id, u.full_name, c.id AS class_id, "
            "('Class ' || c.grade || ' ' || c.division || ' (' || c.academic_year || ')') AS grp "
            "FROM teacher_class_assignments a JOIN classes c ON c.id = a.class_id "
            "JOIN class_enrollments e ON e.class_id = c.id AND e.status = 'approved' "
            "JOIN users u ON u.id = e.student_user_id WHERE a.teacher_user_id = ? ORDER BY c.grade, c.division, u.full_name",
            (uid,)).fetchall())
    if role == "parent":
        return rows_to_dicts(conn.execute(
            "SELECT u.id, u.full_name, NULL AS class_id, 'Your children' AS grp FROM parent_student_links l "
            "JOIN users u ON u.id = l.student_user_id WHERE l.parent_user_id = ? AND l.status = 'active' ORDER BY u.full_name",
            (uid,)).fetchall())
    return []


def _student_of(conn, user_id: int) -> Optional[dict]:
    return row_to_dict(conn.execute("SELECT s.* FROM learner_links l JOIN students s ON s.id = l.student_id "
                                    "WHERE l.user_id = ?", (user_id,)).fetchone())


def _summary(conn, student: Optional[dict]) -> dict:
    if student is None:
        return {"started": False, "topics_started": 0, "active": [], "confirmed_gaps": 0, "needs_review": 0,
                "skills_mastered": 0, "answers": 0, "correct": 0, "last_activity": None}
    cases = rows_to_dicts(conn.execute(
        f"SELECT cases.*, {orch._TOPIC_SQL} AS topic_id FROM cases WHERE student_id=? ORDER BY id",
        (student["id"],)).fetchall())
    latest = {}
    for c in cases:
        latest[c["topic_id"]] = c
    ids = [c["id"] for c in cases] or [0]
    marks = ",".join("?" * len(ids))
    gaps = rows_to_dicts(conn.execute(f"SELECT * FROM gaps WHERE case_id IN ({marks})", ids).fetchall())
    resp = conn.execute(f"SELECT COUNT(*) n, COALESCE(SUM(r.is_correct),0) c, MAX(r.created_at) last FROM responses r "
                        f"JOIN assessments a ON a.id=r.assessment_id WHERE a.case_id IN ({marks}) AND a.kind!='practice'",
                        ids).fetchone()
    mastered = conn.execute("SELECT COUNT(*) FROM skill_mastery WHERE student_id=? AND status='mastered'",
                            (student["id"],)).fetchone()[0]
    active = [{"topic_id": t, "topic": topics().get(t, {}).get("name", t), "stage": c["stage"],
               "stage_label": orch.STAGE_LABELS.get(c["stage"], c["stage"])}
              for t, c in latest.items() if c["stage"] in orch.ACTIVE_STAGES]
    return {"started": True, "topics_started": len(latest), "active": active,
            "confirmed_gaps": sum(1 for g in gaps if g["status"] in ("confirmed", "still_present")),
            "needs_review": sum(1 for c in latest.values() if c["stage"] == "teacher_review"),
            "skills_mastered": mastered, "answers": resp["n"], "correct": resp["c"], "last_activity": resp["last"]}


# ---------------------------------------------------------------- routes

@router.get("/students")
def students(user: dict = Depends(active_user)):
    if user["role"] not in VIEWER_ROLES:
        raise AccountError("Not available for this account.", 403)
    with db.transaction() as conn:
        groups: dict[str, dict] = {}
        common: dict[str, Counter] = {}
        seen = set()
        for c in _candidates(conn, user):
            if (c["id"], c["grp"]) in seen or not permissions.access_via(conn, user, c["id"], "progress"):
                continue
            seen.add((c["id"], c["grp"]))
            student = _student_of(conn, c["id"])
            g = groups.setdefault(c["grp"], {"label": c["grp"], "class_id": c["class_id"], "students": []})
            g["students"].append({"user_id": c["id"], "name": c["full_name"], **_summary(conn, student)})
            if student and user["role"] == "teacher":
                cnt = common.setdefault(c["grp"], Counter())
                for r in conn.execute(
                        "SELECT DISTINCT g.misconception, g.skill_id FROM gaps g JOIN cases k ON k.id=g.case_id "
                        "WHERE k.student_id=? AND g.status IN ('confirmed','still_present','resolved')",
                        (student["id"],)).fetchall():
                    label = (misconceptions().get(r["misconception"] or "") or {}).get("label") or skill_name(r["skill_id"])
                    cnt[label] += 1
        queue, interventions = [], []
        if user["role"] == "teacher":
            for g in groups.values():
                for srow in g["students"]:
                    student = _student_of(conn, srow["user_id"])
                    if not student:
                        continue
                    for c in rows_to_dicts(conn.execute(
                            f"SELECT cases.*, {orch._TOPIC_SQL} AS topic_id FROM cases WHERE student_id=?",
                            (student["id"],)).fetchall()):
                        gap = row_to_dict(conn.execute("SELECT * FROM gaps WHERE case_id=? ORDER BY id DESC LIMIT 1",
                                                       (c["id"],)).fetchone())
                        if c["stage"] == "teacher_review":
                            mis = (misconceptions().get((gap or {}).get("misconception") or "") or {}).get("label")
                            queue.append({"user_id": srow["user_id"], "student": srow["name"], "case_id": c["id"],
                                          "topic": topics().get(c["topic_id"], {}).get("name", c["topic_id"]),
                                          "skill": skill_name(gap["skill_id"]) if gap else None, "suspected": mis,
                                          "reason": _review_reason(c["closed_reason"]),
                                          "since": c["updated_at"]})
                        for o in conn.execute("SELECT * FROM teacher_overrides WHERE case_id=?", (c["id"],)).fetchall():
                            interventions.append({"date": o["created_at"], "by": o["teacher_name"], "action": o["action"],
                                                  "reason": o["reason"], "student": srow["name"], "user_id": srow["user_id"],
                                                  "topic": topics().get(c["topic_id"], {}).get("name", c["topic_id"])})
            queue.sort(key=lambda x: x["since"])
            interventions.sort(key=lambda x: x["date"], reverse=True)
        out = []
        for label, g in groups.items():
            st = g["students"]
            g["insights"] = {
                "students": len(st), "started": sum(1 for s in st if s["started"]),
                "needs_review": sum(s["needs_review"] for s in st),
                "common_gaps": [{"label": k, "students": v} for k, v in common.get(label, Counter()).most_common(5)],
            } if user["role"] == "teacher" else None
            if user["role"] == "teacher" and g["class_id"] is not None:
                g["overview"] = history.class_overview(conn, [
                    {"user_id": s["user_id"], "name": s["name"], "student": _student_of(conn, s["user_id"])} for s in st])
            for s in st:
                d = history.demo_profile(conn, s["user_id"])
                s["student_code"] = d["student_code"] if d else None
            out.append(g)
        return {"role": user["role"], "groups": out, "queue": queue, "interventions": interventions[:15]}


@router.get("/students/{user_id}")
def student_detail(user_id: int, user: dict = Depends(active_user)):
    with db.transaction() as conn:
        via = permissions.require(conn, user, user_id, "progress")      # logs the access
        can_gaps = bool(permissions.access_via(conn, user, user_id, "gaps"))
        can_assess = bool(permissions.access_via(conn, user, user_id, "assessments"))
        can_review = user["role"] == "teacher" and via == "teacher_class"
        person = conn.execute("SELECT id, full_name, role FROM users WHERE id=?", (user_id,)).fetchone()
        student = _student_of(conn, user_id)
        base = {"user_id": user_id, "name": person["full_name"], "access_via": via, "can_review": can_review,
                "can_see_gaps": can_gaps, "can_see_assessments": can_assess}
        base["demo"] = history.demo_profile(conn, user_id)
        if student is None:
            return {**base, "started": False, "topics": [], "skills": []}
        mastery = {r["skill_id"]: dict(r) for r in conn.execute(
            "SELECT * FROM skill_mastery WHERE student_id=?", (student["id"],)).fetchall()}
        cases = rows_to_dicts(conn.execute(
            f"SELECT cases.*, {orch._TOPIC_SQL} AS topic_id FROM cases WHERE student_id=? ORDER BY id DESC",
            (student["id"],)).fetchall())
        by_topic: dict[str, list] = {}
        for c in cases:
            by_topic.setdefault(c["topic_id"], []).append(c)
        topic_out = []
        for tid, cs in by_topic.items():
            t = topics().get(tid, {"name": tid, "skills": []})
            rounds = []
            for c in cs[:6]:
                d = orch.case_detail(c["id"], conn)
                r = {"case_id": c["id"], "date": c["created_at"], "stage": c["stage"],
                     "stage_label": d["stage_label"], "closed_reason": c["closed_reason"]}
                gap = d["gap"]
                if gap and can_gaps:
                    mis = misconceptions().get(gap["misconception"] or "") or {}
                    ev = gap.get("evidence") or {}
                    ver_reason = ev.get("verification_reason")
                    r["gap"] = {"skill_id": gap["skill_id"], "skill": skill_name(gap["skill_id"]),
                                "status": gap["status"], "status_label": GAP_STATUS.get(gap["status"], gap["status"]),
                                "misconception": mis.get("label"), "explanation": mis.get("explanation"),
                                "hypothesis": gap.get("hypothesis"), "verified_by": gap.get("verified_by"),
                                "checker_reason": ver_reason,
                                "evidence": [{"prompt": e.get("prompt"), "answer": e.get("answer")}
                                             for e in (ev.get("diagnosis") or [])][:4],
                                "check_evidence": [{"prompt": e.get("prompt"), "answer": e.get("answer"),
                                                    "correct": bool(e.get("is_correct")),
                                                    "supports_gap": bool(e.get("supports_gap"))}
                                                   for e in (ev.get("verification") or [])],
                                "retests": [{"score": x.get("score"), "passed": x.get("passed")}
                                            for x in ev.get("retests", [])]}
                if d["plan"] and can_gaps:
                    r["plan"] = {"focus": skill_name(d["plan"]["focus_skill"]), "rationale": d["plan"]["rationale"],
                                 "created_by": d["plan"]["created_by"]}
                if can_assess:
                    r["assessments"] = [{"kind": a["kind"], "answered": a["answered"], "total": a["total"],
                                         "correct": sum(1 for q in a["questions"] if q.get("is_correct")),
                                         "status": a["status"]} for a in d["assessments"]]
                if can_review:
                    r["overrides"] = [{"action": o["action"], "by": o["teacher_name"], "reason": o["reason"],
                                       "date": o["created_at"]} for o in d["overrides"]]
                    r["actions"] = {
                        "decide": bool(gap) and c["stage"] not in ("diagnostic", "verification", "completed", "closed"),
                        "focus": bool(gap) and gap["status"] in ("confirmed", "still_present")
                                 and c["stage"] in ("learning", "retest_pending", "teacher_review"),
                    }
                rounds.append(r)
            topic_out.append({"topic_id": tid, "topic": t["name"], "rounds": rounds,
                              "skills": [{"skill_id": s, "name": skill_name(s),
                                          "status": MASTERY[mastery.get(s, {}).get("status", "not_assessed")],
                                          "correct": mastery.get(s, {}).get("correct", 0),
                                          "attempts": mastery.get(s, {}).get("attempts", 0)} for s in t["skills"]]})
        teachable = [{"skill_id": s, "name": skill_name(s)} for s in sorted(lessons(), key=skill_name)] if can_review else []
        return {**base, "started": True, "grade": student["grade"], "summary": _summary(conn, student),
                "topics": topic_out, "teachable_skills": teachable}


@router.get("/students/{user_id}/history")
def student_history(user_id: int, user: dict = Depends(active_user)):
    """The same six-month history the student sees, for a teacher of their class or a parent/viewer with permission.
    Misconception names and the Checker's reasons are shown only to viewers allowed to see gaps."""
    with db.transaction() as conn:
        permissions.require(conn, user, user_id, "progress")      # logs the access
        can_gaps = bool(permissions.access_via(conn, user, user_id, "gaps"))
        student = _student_of(conn, user_id)
        if student is None:
            return {"started": False, "demo": history.demo_profile(conn, user_id)}
        return {"started": True, **history.student_history(conn, student, user_id, show_gaps=can_gaps)}


def _teacher_case(case_id: int, user: dict) -> str:
    """The case must belong to a student in one of this teacher's classes. Returns the audit name."""
    if user["role"] != "teacher":
        raise AccountError("Only the student's teacher can do this.", 403)
    with db.transaction() as conn:
        case = row_to_dict(conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone())
        owner = case and conn.execute("SELECT user_id FROM learner_links WHERE student_id=?",
                                      (case["student_id"],)).fetchone()
        if not owner or permissions.access_via(conn, user, owner["user_id"], "gaps") != "teacher_class":
            raise AccountError("Not found.", 404)
        permissions.require(conn, user, owner["user_id"], "gaps")
    return f"{user['full_name'][:44]} (#{user['id']})"


@router.post("/cases/{case_id}/decision")
def decide(case_id: int, body: Decision, user: dict = Depends(active_user)):
    who = _teacher_case(case_id, user)
    if body.focus_skill and body.focus_skill not in skills_by_id():
        raise orch.WorkflowError("Unknown skill.", 400)
    d = orch.teacher_gap_decision(case_id, body.decision, who, body.reason, body.focus_skill)
    return {"ok": True, "stage": d["stage"], "stage_label": d["stage_label"]}


@router.post("/cases/{case_id}/focus")
def set_focus(case_id: int, body: Focus, user: dict = Depends(active_user)):
    who = _teacher_case(case_id, user)
    d = orch.teacher_set_focus(case_id, body.focus_skill, who, body.reason)
    return {"ok": True, "stage": d["stage"], "stage_label": d["stage_label"]}


@router.post("/cases/{case_id}/note")
def add_note(case_id: int, body: Note, user: dict = Depends(active_user)):
    who = _teacher_case(case_id, user)
    orch.teacher_note(case_id, who, body.note)
    return {"ok": True}
