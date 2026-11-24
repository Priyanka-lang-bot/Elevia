"""Learning history, subject progress, skill map and class insights, computed from stored records only.

Sources (nothing else is read, nothing is estimated):
  responses           every answer, with its assessment kind and whether it was right
  agent_runs          what each role did and decided: Diagnoser diagnose, Checker evaluate_verification /
                      schedule_retest / evaluate_retest, Tutor teach (with timestamps and outputs)
  teacher_overrides   every teacher decision and note, with the reason
  skill_mastery       the current status of each skill (mastered only after a passed retest)
  cases / gaps        which topic a case belongs to and whether a gap is still open now

Monthly figures are sums of the same events the timeline lists, so the two always agree; `check_totals`
verifies that for tests.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Optional

from . import clock
from . import orchestrator as orch
from .content import curriculum, lessons, misconceptions, skill_name, topics
from .db import row_to_dict, rows_to_dicts

HISTORY_DAYS = 182
OPEN_STAGES = ("diagnostic", "verification", "learning", "retest_pending", "retest", "teacher_review")
MONTH_KEYS = ("answers", "correct", "practice", "checkins", "suspected", "confirmed", "rejected", "inconclusive", "lessons",
              "retests_passed", "retests_failed", "mastered", "teacher")
VERDICT_TEXT = {"confirmed": "Double-check confirmed the gap",
                "rejected": "Double-check: probably a slip, so the gap was rejected",
                "inconclusive": "Double-check was mixed, so it went to the teacher"}
OVERRIDE_TEXT = {"confirm_gap": "Teacher confirmed the gap", "reject_gap": "Teacher rejected the gap",
                 "change_focus": "Teacher changed the learning focus", "note": "Teacher added a note"}


def _month_label(key: str) -> str:
    y, m = int(key[:4]), int(key[5:])
    return date(y, m, 1).strftime("%b %Y")


def _months(start: date, end: date) -> list[str]:
    out, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def demo_profile(conn, user_id: int) -> Optional[dict]:
    row = row_to_dict(conn.execute("SELECT * FROM demo_profiles WHERE user_id=?", (user_id,)).fetchone())
    if not row:
        return None
    school = conn.execute(
        "SELECT s.name, c.grade, c.division, c.academic_year FROM class_enrollments e JOIN classes c ON c.id=e.class_id "
        "JOIN schools s ON s.id=c.school_id WHERE e.student_user_id=? AND e.status='approved' LIMIT 1", (user_id,)).fetchone()
    return {"student_code": row["student_code"], "reference_date": row["reference_date"],
            "period_start": row["period_start"],
            "school": school["name"] if school else None,
            "class": f"Class {school['grade']} {school['division']}" if school else None,
            "academic_year": school["academic_year"] if school else None,
            "note": "Demonstration account. Fictional student; the history was produced by running ELEVIA's real "
                    "rules on simulated answers, with dates set across the six months before the reference date."}


def _subject_of(topic_id: str) -> tuple[str, str]:
    t = topics().get(topic_id) or {}
    sid = t.get("subject", "mathematics")
    name = next((s["name"] for s in curriculum()["subjects"] if s["id"] == sid), sid)
    return sid, name


def _load(conn, student_id: int) -> dict:
    cases = rows_to_dicts(conn.execute(f"SELECT cases.*, {orch._TOPIC_SQL} AS topic_id FROM cases WHERE student_id=?",
                                       (student_id,)).fetchall())
    ids = [c["id"] for c in cases] or [0]
    q = ",".join("?" * len(ids))
    runs = rows_to_dicts(conn.execute(
        f"SELECT case_id, agent, step, status, output, finished_at FROM agent_runs WHERE case_id IN ({q}) "
        "AND status='succeeded' AND step IN ('diagnose','evaluate_verification','teach','schedule_retest','evaluate_retest')",
        ids).fetchall())
    resp = rows_to_dicts(conn.execute(
        "SELECT r.created_at, r.is_correct, a.kind, a.case_id FROM responses r JOIN assessments a ON a.id=r.assessment_id "
        "WHERE r.student_id=?", (student_id,)).fetchall())
    overrides = rows_to_dicts(conn.execute(
        f"SELECT * FROM teacher_overrides WHERE case_id IN ({q})", ids).fetchall())
    gaps = {r["case_id"]: dict(r) for r in conn.execute(
        f"SELECT * FROM gaps WHERE id IN (SELECT MAX(id) FROM gaps WHERE case_id IN ({q}) GROUP BY case_id)", ids).fetchall()}
    mastery = {r["skill_id"]: dict(r) for r in conn.execute(
        "SELECT * FROM skill_mastery WHERE student_id=?", (student_id,)).fetchall()}
    open_retests = rows_to_dicts(conn.execute(
        f"SELECT case_id, available_at FROM assessments WHERE case_id IN ({q}) AND kind='retest' AND status='open'",
        ids).fetchall())
    return {"cases": {c["id"]: c for c in cases}, "runs": runs, "responses": resp, "overrides": overrides,
            "gaps": gaps, "mastery": mastery, "open_retests": open_retests}


def _events(data: dict, show_gaps: bool) -> list[dict]:
    """One entry per thing that happened, newest last. Misconception names only when gaps may be shown."""
    mis = misconceptions()
    ev = []

    def add(when, kind, case_id, text, detail=None, **extra):
        c = data["cases"][case_id]
        sid, sname = _subject_of(c["topic_id"])
        ev.append({"date": when, "kind": kind, "case_id": case_id, "subject_id": sid, "subject": sname,
                   "topic_id": c["topic_id"], "topic": topics().get(c["topic_id"], {}).get("name", c["topic_id"]),
                   "text": text, "detail": detail, **extra})

    for r in data["runs"]:
        out = r["output"] if isinstance(r["output"], dict) else json.loads(r["output"] or "{}")
        cid, when = r["case_id"], r["finished_at"]
        if r["step"] == "diagnose":
            prim = out.get("primary") or {}
            if out.get("has_gap"):
                label = (mis.get(prim.get("misconception") or "") or {}).get("label") if show_gaps else None
                add(when, "suspected", cid, "Possible gap spotted" + (f": {label.lower()}" if label else ""),
                    f"Check-in score {out.get('score', {}).get('correct', '?')}/{out.get('score', {}).get('total', '?')}")
            else:
                add(when, "no_gap", cid, "Check-in: no gap found",
                    f"Check-in score {out.get('score', {}).get('correct', '?')}/{out.get('score', {}).get('total', '?')}")
        elif r["step"] == "evaluate_verification":
            v = out.get("verdict")
            add(when, v, cid, VERDICT_TEXT.get(v, "Double-check finished"), out.get("reason") if show_gaps else None)
        elif r["step"] == "teach":
            add(when, "lesson", cid, f"Lesson: {out.get('title') or skill_name(out.get('skill_id', ''))}",
                f"Focus: {out.get('skill_name') or skill_name(out.get('skill_id', ''))}")
        elif r["step"] == "schedule_retest" and out.get("ok"):
            add(when, "retest_booked", cid, "Retest booked", None, due=out.get("available_at"))
        elif r["step"] == "evaluate_retest":
            sc = out.get("score") or {}
            passed = bool(out.get("passed"))
            add(when, "retest_passed" if passed else "retest_failed", cid,
                (f"Retest passed {sc.get('correct')}/{sc.get('total')}: skill mastered" if passed
                 else f"Retest {sc.get('correct')}/{sc.get('total')}: not yet, so a new plan was made"))
    for o in data["overrides"]:
        add(o["created_at"], "teacher", o["case_id"], OVERRIDE_TEXT.get(o["action"], "Teacher action"),
            o["reason"], by=o["teacher_name"].split(" (#")[0], action=o["action"])
    ev.sort(key=lambda e: (e["date"] or "", e["kind"]))
    return ev


def student_history(conn, student: dict, user_id: int, show_gaps: bool = True) -> dict:
    data = _load(conn, student["id"])
    events = _events(data, show_gaps)
    demo = demo_profile(conn, user_id)
    now = clock.now()
    start = date.fromisoformat(demo["period_start"]) if demo else (now - timedelta(days=HISTORY_DAYS)).date()
    keys = _months(start, now.date())
    months = {k: dict.fromkeys(MONTH_KEYS, 0) for k in keys}

    def bucket(when):
        k = (when or "")[:7]
        return months.get(k)

    for r in data["responses"]:
        b = bucket(r["created_at"])
        if b is None:
            continue
        if r["kind"] == "practice":            # practice gives feedback but never counts towards progress
            b["practice"] += 1
            continue
        b["answers"] += 1
        b["correct"] += int(r["is_correct"])
    count_kind = {"suspected": "suspected", "no_gap": None, "confirmed": "confirmed", "rejected": "rejected",
                  "inconclusive": "inconclusive", "lesson": "lessons", "retest_passed": "retests_passed",
                  "retest_failed": "retests_failed", "teacher": "teacher"}
    for e in events:
        b = bucket(e["date"])
        if b is None:
            continue
        if e["kind"] in ("suspected", "no_gap"):
            b["checkins"] += 1
        k = count_kind.get(e["kind"])
        if k:
            b[k] += 1
        if e["kind"] == "retest_passed":
            b["mastered"] += 1
    month_list = [{"key": k, "label": _month_label(k), **v,
                   "accuracy": round(100 * v["correct"] / v["answers"]) if v["answers"] else None} for k, v in months.items()]
    totals = {k: sum(m[k] for m in month_list) for k in MONTH_KEYS}
    upcoming = sorted(
        [{"case_id": r["case_id"], "due": r["available_at"], "topic_id": data["cases"][r["case_id"]]["topic_id"],
          "topic": topics().get(data["cases"][r["case_id"]]["topic_id"], {}).get("name"),
          "subject": _subject_of(data["cases"][r["case_id"]]["topic_id"])[1]}
         for r in data["open_retests"] if r["available_at"] and r["available_at"] > now.isoformat()],
        key=lambda x: x["due"])
    return {"demo": demo, "period": {"start": start.isoformat(), "end": now.date().isoformat()},
            "months": month_list, "totals": totals, "events": events[::-1][:80], "event_count": len(events),
            "upcoming_retests": upcoming, "subjects": subject_progress(data), "skill_map": skill_map(data, show_gaps)}


def _open_gap_skills(data: dict) -> dict[str, str]:
    """skill -> status for gaps in cases that are still open."""
    out = {}
    for cid, c in data["cases"].items():
        g = data["gaps"].get(cid)
        if c["stage"] in OPEN_STAGES and g and g["status"] in ("suspected", "confirmed", "inconclusive", "still_present"):
            out[g["skill_id"]] = g["status"]
    return out


def subject_progress(data: dict) -> list[dict]:
    cur = curriculum()
    started_topics = {c["topic_id"] for c in data["cases"].values()}
    open_gaps = _open_gap_skills(data)
    per_subject_resp = defaultdict(lambda: [0, 0])
    for r in data["responses"]:
        if r["kind"] == "practice":
            continue
        sid = _subject_of(data["cases"][r["case_id"]]["topic_id"])[0]
        per_subject_resp[sid][0] += 1
        per_subject_resp[sid][1] += int(r["is_correct"])
    out = []
    for s in cur["subjects"]:
        skills = [k for t in s["topics"] for k in topics()[t]["skills"]]
        mastered = sum(1 for k in skills if data["mastery"].get(k, {}).get("status") == "mastered")
        n, c = per_subject_resp[s["id"]]
        out.append({"id": s["id"], "name": s["name"], "color": s["color"],
                    "topics_total": len(s["topics"]), "topics_started": len([t for t in s["topics"] if t in started_topics]),
                    "skills_total": len(skills), "skills_mastered": mastered,
                    "open_gaps": sum(1 for k in skills if k in open_gaps),
                    "answers": n, "correct": c, "accuracy": round(100 * c / n) if n else None,
                    "planned": s.get("planned", [])})
    return out


def skill_map(data: dict, show_gaps: bool = True) -> list[dict]:
    """Every playable skill, grouped by subject and topic, with what the records say about it now."""
    open_gaps = _open_gap_skills(data)
    seen_topics = {c["topic_id"] for c in data["cases"].values()}
    out = []
    for s in curriculum()["subjects"]:
        tlist = []
        for tid in s["topics"]:
            t = topics()[tid]
            sk = []
            for k in t["skills"]:
                m = data["mastery"].get(k, {})
                if m.get("status") == "mastered":
                    state = "mastered"
                elif k in open_gaps:
                    state = "working" if show_gaps else "checked"
                elif m.get("attempts"):
                    state = "checked"
                else:
                    state = "not_started"
                sk.append({"skill_id": k, "name": skill_name(k), "state": state})
            tlist.append({"topic_id": tid, "topic": t["name"], "started": tid in seen_topics, "skills": sk})
        out.append({"id": s["id"], "name": s["name"], "color": s["color"], "topics": tlist})
    return out


def check_totals(h: dict) -> bool:
    """The monthly figures add up to the totals, and the totals match the listed events."""
    kinds = Counter(e["kind"] for e in h["events"]) if h["event_count"] <= 80 else None
    ok = all(sum(m[k] for m in h["months"]) == h["totals"][k] for k in MONTH_KEYS)
    if kinds is not None:
        ok = ok and kinds["retest_passed"] == h["totals"]["retests_passed"] and kinds["lesson"] == h["totals"]["lessons"]
    return ok


# ---------------------------------------------------------------- class overview (teacher)

def class_overview(conn, roster: list[dict]) -> dict:
    """roster: [{"user_id", "name", "student": students-row or None}]. Everything is computed from records."""
    now = clock.now()
    per = []
    for r in roster:
        if not r["student"]:
            per.append({**r, "data": None, "events": []})
            continue
        d = _load(conn, r["student"]["id"])
        per.append({**r, "data": d, "events": _events(d, True)})
    start = min([date.fromisoformat(p["demo"]["period_start"]) for p in
                 [{"demo": demo_profile(conn, r["user_id"])} for r in roster] if p["demo"]] or
                [(now - timedelta(days=HISTORY_DAYS)).date()])
    keys = _months(start, now.date())
    trend = {k: {"answers": 0, "correct": 0, "mastered": 0, "confirmed": 0, "active": set()} for k in keys}
    subj = defaultdict(lambda: {"answers": 0, "correct": 0, "open_gaps": 0, "mastered": 0, "students": set()})
    upcoming, mastered_recent, attention = [], [], []
    topic_trouble, mis_students, improved = Counter(), defaultdict(set), []
    failed_by_case = Counter()
    for p in per:
        d = p["data"]
        if d is None:
            continue
        for r in d["responses"]:
            if r["kind"] == "practice":
                continue
            k = r["created_at"][:7]
            sid = _subject_of(d["cases"][r["case_id"]]["topic_id"])[0]
            subj[sid]["answers"] += 1
            subj[sid]["correct"] += int(r["is_correct"])
            subj[sid]["students"].add(p["user_id"])
            if k in trend:
                trend[k]["answers"] += 1
                trend[k]["correct"] += int(r["is_correct"])
                trend[k]["active"].add(p["user_id"])
        for e in p["events"]:
            k = e["date"][:7]
            if e["kind"] == "retest_passed":
                subj[e["subject_id"]]["mastered"] += 1
                if k in trend:
                    trend[k]["mastered"] += 1
                if e["date"] >= (now - timedelta(days=45)).isoformat():
                    mastered_recent.append({"student": p["name"], "user_id": p["user_id"], "topic": e["topic"],
                                            "skill": skill_name(d["gaps"][e["case_id"]]["skill_id"]), "date": e["date"]})
                if failed_by_case[e["case_id"]]:
                    improved.append({"student": p["name"], "user_id": p["user_id"], "topic": e["topic"],
                                     "skill": skill_name(d["gaps"][e["case_id"]]["skill_id"]),
                                     "failed_first": failed_by_case[e["case_id"]], "date": e["date"]})
            if e["kind"] == "retest_failed":
                failed_by_case[e["case_id"]] += 1
                topic_trouble[e["topic"]] += 1
            if e["kind"] == "confirmed" or (e["kind"] == "teacher" and e.get("action") == "confirm_gap"):
                topic_trouble[e["topic"]] += 1
                if k in trend:
                    trend[k]["confirmed"] += 1
                g = d["gaps"].get(e["case_id"])
                label = (misconceptions().get((g or {}).get("misconception") or "") or {}).get("label")
                if label:
                    mis_students[label].add(p["user_id"])
        open_gaps = _open_gap_skills(d)
        for cid, c in d["cases"].items():
            g = d["gaps"].get(cid)
            if c["stage"] in OPEN_STAGES and g and g["skill_id"] in open_gaps and g["status"] in ("confirmed", "still_present"):
                subj[_subject_of(c["topic_id"])[0]]["open_gaps"] += 1
        for r in d["open_retests"]:
            if r["available_at"] and r["available_at"] > now.isoformat():
                c = d["cases"][r["case_id"]]
                upcoming.append({"student": p["name"], "user_id": p["user_id"], "due": r["available_at"],
                                 "topic": topics().get(c["topic_id"], {}).get("name")})
        reasons = []
        review = sum(1 for c in d["cases"].values() if c["stage"] == "teacher_review")
        if review:
            reasons.append(f"{review} case{'s' if review > 1 else ''} waiting for your review")
        repeat = [cid for cid, n in failed_by_case.items() if n >= 2 and cid in d["cases"]
                  and d["cases"][cid]["stage"] != "completed"]
        if repeat:
            reasons.append("failed the same retest more than once")
        n_open = sum(1 for k, v in open_gaps.items() if v in ("confirmed", "still_present"))
        if n_open >= 2:
            reasons.append(f"{n_open} confirmed gaps still open")
        if reasons:
            attention.append({"student": p["name"], "user_id": p["user_id"], "reasons": reasons})
    repeated = [{"student": p["name"], "user_id": p["user_id"], "topic": topics().get(p["data"]["cases"][cid]["topic_id"], {}).get("name"),
                 "failed": n, "status": orch.STAGE_LABELS.get(p["data"]["cases"][cid]["stage"], p["data"]["cases"][cid]["stage"])}
                for p in per if p["data"] for cid, n in failed_by_case.items() if n >= 2 and cid in p["data"]["cases"]]
    cur = curriculum()
    return {
        "subjects": [{"id": s["id"], "name": s["name"], "color": s["color"], "students": len(subj[s["id"]]["students"]),
                      "answers": subj[s["id"]]["answers"],
                      "accuracy": round(100 * subj[s["id"]]["correct"] / subj[s["id"]]["answers"]) if subj[s["id"]]["answers"] else None,
                      "open_gaps": subj[s["id"]]["open_gaps"], "mastered": subj[s["id"]]["mastered"]} for s in cur["subjects"]],
        "trend": [{"key": k, "label": _month_label(k), "answers": v["answers"],
                   "accuracy": round(100 * v["correct"] / v["answers"]) if v["answers"] else None,
                   "mastered": v["mastered"], "confirmed": v["confirmed"], "active_students": len(v["active"])}
                  for k, v in trend.items()],
        "upcoming_retests": sorted(upcoming, key=lambda x: x["due"]),
        "recently_mastered": sorted(mastered_recent, key=lambda x: x["date"], reverse=True)[:8],
        "needs_attention": attention,
        "difficult_topics": [{"topic": t, "count": n} for t, n in topic_trouble.most_common(5)],
        "frequent_misconceptions": [{"label": m, "count": len(u)} for m, u in
                                    sorted(mis_students.items(), key=lambda x: (-len(x[1]), x[0]))[:5]],
        "repeated_failed_retests": repeated,
        "most_improved": sorted(improved, key=lambda x: x["date"], reverse=True)[:6],
        "totals": {"students": len(roster), "started": sum(1 for p in per if p["data"] and p["data"]["cases"]),
                   "open_confirmed_gaps": sum(s["open_gaps"] for s in subj.values()),
                   "upcoming_retests": len(upcoming), "mastered_recently": len(mastered_recent),
                   "needs_attention": len(attention)},
    }


def lessons_completed(events: list[dict]) -> int:
    return sum(1 for e in events if e["kind"] == "lesson")


