"""The six-month demo history is internally consistent: every claim on a dashboard is backed by records that the
real workflow wrote. Also checks the history endpoints' access rules and that seeding is deterministic."""
import json
from datetime import date

from tests.test_accounts import H, db_one, make_learner
from tests.test_demo import PW, demo_script

REF = date.today()


def rows(sql, *a):
    from backend import db
    with db.transaction() as c:
        return [dict(r) for r in c.execute(sql, a).fetchall()]


def login(client, ident):
    r = client.post("/auth/login", json={"identifier": ident, "password": PW}, headers={"X-Elevia-Web": "1"})
    assert r.status_code == 200, r.text
    return r.cookies.get("elevia_session") or r.headers["set-cookie"].split("elevia_session=")[1].split(";")[0]


def test_six_month_history_is_backed_by_records(client):
    out = demo_script.seed(reference_date=REF, password=PW)
    assert out["period_start"] == date.fromordinal(REF.toordinal() - 182).isoformat()
    riya_uid = db_one("SELECT ref_id FROM demo_registry WHERE slug='riya'")[0]
    sid = db_one("SELECT student_id FROM learner_links WHERE user_id=?", riya_uid)[0]
    tok = login(client, "riya.demo")
    h = client.get("/learn/history", headers=H(tok)).json()
    dash = client.get("/learn/dashboard", headers=H(tok)).json()

    # who she is, clearly labelled as a demonstration account
    assert h["demo"]["student_code"] == "DEMO-09-001" and h["demo"]["class"] == "Class 9 A"
    assert h["demo"]["school"] == "ELEVIA Demonstration School" and h["demo"]["academic_year"] == "2026-27"
    assert dash["demo"]["student_code"] == "DEMO-09-001" and dash["student"]["grade"] == 9
    assert "Demonstration account" in h["demo"]["note"]

    # the timeline spans six months and every record sits inside it
    assert len(h["months"]) >= 6
    first = min(r["created_at"] for r in rows("SELECT created_at FROM cases WHERE student_id=?", sid))
    assert first[:10] >= h["period"]["start"]
    assert sum(1 for m in h["months"] if m["answers"]) >= 6                          # active every month

    # monthly figures add up, and agree with the dashboard and the database
    from backend import history
    assert history.check_totals(h)
    graded = rows("SELECT r.is_correct FROM responses r JOIN assessments a ON a.id=r.assessment_id "
                  "WHERE r.student_id=? AND a.kind!='practice'", sid)
    assert h["totals"]["answers"] == len(graded) == dash["answers"]["total"]
    assert h["totals"]["correct"] == sum(r["is_correct"] for r in graded) == dash["answers"]["correct"]
    assert sum(s["answers"] for s in h["subjects"]) == h["totals"]["answers"]
    assert h["totals"]["checkins"] == len(rows("SELECT id FROM cases WHERE student_id=?", sid))

    # all five Class 9 subjects have real activity
    assert {s["name"] for s in h["subjects"] if s["answers"]} == {
        "Mathematics", "Science", "English", "Social Science", "Computer Science"}

    # mastered skills: each has a passed retest (>= 2 of 3 on new questions) recorded by the Checker
    mastered = [r["skill_id"] for r in rows("SELECT skill_id FROM skill_mastery WHERE student_id=? AND status='mastered'", sid)]
    assert len(mastered) == h["totals"]["mastered"] == dash["totals"]["skills_mastered"] == 8
    for skill in mastered:
        ok = rows("SELECT ar.output FROM agent_runs ar JOIN gaps g ON g.case_id=ar.case_id "
                  "WHERE ar.step='evaluate_retest' AND g.skill_id=? AND g.case_id IN (SELECT id FROM cases WHERE student_id=?)",
                  skill, sid)
        outs = [json.loads(o["output"]) if isinstance(o["output"], str) else o["output"] for o in ok]
        assert any(o["passed"] and o["score"]["correct"] >= 2 for o in outs), skill
    in_map = [k["skill_id"] for s in h["skill_map"] for t in s["topics"] for k in t["skills"] if k["state"] == "mastered"]
    assert sorted(in_map) == sorted(mastered)

    # confirmed gaps: backed by the Checker's double-check, or by a logged teacher decision
    for g in rows("SELECT g.* FROM gaps g JOIN cases c ON c.id=g.case_id WHERE c.student_id=? "
                  "AND g.status IN ('confirmed','still_present','resolved')", sid):
        if (g["verified_by"] or "").startswith("teacher:"):
            assert rows("SELECT 1 FROM teacher_overrides WHERE case_id=? AND action='confirm_gap'", g["case_id"])
        else:
            v = rows("SELECT output FROM agent_runs WHERE case_id=? AND step='evaluate_verification'", g["case_id"])
            assert v and json.loads(v[0]["output"])["verdict"] == "confirmed"

    # every lesson in the history exists as a stored lesson
    assert h["totals"]["lessons"] == len(rows("SELECT l.id FROM lessons l JOIN cases c ON c.id=l.case_id WHERE c.student_id=?", sid))

    # the upcoming retest has a real, future date; no retest was ever started early while seeding
    assert h["upcoming_retests"] and all(u["due"] > REF.isoformat() for u in h["upcoming_retests"])
    assert db_one("SELECT COUNT(*) FROM agent_runs WHERE step='early_retest_override'")[0] == 0

    # teacher actions in her history are saved override records, each with a reason
    t_events = [e for e in h["events"] if e["kind"] == "teacher"]
    saved = rows("SELECT * FROM teacher_overrides WHERE case_id IN (SELECT id FROM cases WHERE student_id=?)", sid)
    assert len(t_events) == len(saved) == h["totals"]["teacher"] == 3
    assert all(len(s["reason"]) >= 5 for s in saved)

    # failed retests were followed by a new plan (the Planner, or a teacher's change of focus)
    for e in [e for e in h["events"] if e["kind"] == "retest_failed"]:
        assert rows("SELECT 1 FROM plans WHERE case_id=? AND created_at>=?", e["case_id"], e["date"])


def test_teacher_class_overview_and_insights_come_from_records(client):
    demo_script.seed(reference_date=REF, password=PW)
    t = client.get("/progress/students", headers=H(login(client, "demo.teacher@example.com"))).json()
    g = t["groups"][0]
    o = g["overview"]
    assert g["label"].startswith("Class 9 A") and o["totals"]["students"] == 5
    codes = {s["name"]: s["student_code"] for s in g["students"]}
    assert codes["Riya Sharma"] == "DEMO-09-001" and codes["Zoya Khan"] == "DEMO-09-005"
    # class answers by subject = sum of each student's own figures
    total = sum(s["answers"] for s in g["students"])
    assert sum(s["answers"] for s in o["subjects"]) == total == sum(m["answers"] for m in o["trend"])
    # Arjun failed the same integers retest twice and the Checker handed the case to the teacher
    rep = o["repeated_failed_retests"]
    assert [(r["student"], r["topic"], r["failed"]) for r in rep] == [("Arjun Patel", "Integers", 2)]
    assert {a["student"] for a in o["needs_attention"]} >= {"Arjun Patel", "Riya Sharma"}
    assert {(u["student"], u["topic"]) for u in o["upcoming_retests"]} == {
        ("Riya Sharma", "Ratio and proportion"), ("Zoya Khan", "Time zones and Indian Standard Time")}
    # "most improved" = a retest passed after a failed one on the same case
    assert {(m["student"], m["skill"]) for m in o["most_improved"]} >= {("Riya Sharma", "Solving two-step equations"),
                                                                          ("Meera Nair", "How many times a loop runs")}
    assert all(m["count"] >= 1 for m in o["frequent_misconceptions"])


def test_teacher_review_is_saved_and_shows_in_the_history(client):
    demo_script.seed(reference_date=REF, password=PW)
    ttok = login(client, "demo.teacher@example.com")
    riya = db_one("SELECT ref_id FROM demo_registry WHERE slug='riya'")[0]
    det = client.get(f"/progress/students/{riya}", headers=H(ttok)).json()
    past = next(t for t in det["topics"] if t["topic_id"] == "past_tense")["rounds"][0]
    assert past["stage"] == "teacher_review" and past["actions"]["decide"]
    ev = past["gap"]
    assert ev["misconception"] and ev["hypothesis"] and ev["checker_reason"].startswith("Mixed evidence")
    assert len(ev["check_evidence"]) == 2 and any(not e["correct"] and not e["supports_gap"] for e in ev["check_evidence"])
    before = client.get(f"/progress/students/{riya}/history", headers=H(ttok)).json()["totals"]["teacher"]
    r = client.post(f"/progress/cases/{past['case_id']}/decision",
                    json={"decision": "confirm", "reason": "Riya wrote 'thinked' in her diary entry today too."}, headers=H(ttok))
    assert r.status_code == 200 and r.json()["stage"] == "learning"
    h = client.get(f"/progress/students/{riya}/history", headers=H(ttok)).json()
    assert h["totals"]["teacher"] == before + 1
    assert h["events"][0]["kind"] in ("teacher", "lesson")
    assert any(e["kind"] == "teacher" and "diary" in (e["detail"] or "") for e in h["events"][:3])
    o = client.get("/progress/students", headers=H(ttok)).json()
    assert o["interventions"][0]["action"] == "confirm_gap" and "diary" in o["interventions"][0]["reason"]
    # and Riya sees her lesson
    rs = client.get("/learn/state?topic=past_tense", headers=H(login(client, "riya.demo"))).json()
    assert rs["phase"] == "learn"


def test_history_endpoints_respect_permissions(client):
    demo_script.seed(reference_date=REF, password=PW)
    riya = db_one("SELECT ref_id FROM demo_registry WHERE slug='riya'")[0]
    arjun = db_one("SELECT ref_id FROM demo_registry WHERE slug='arjun'")[0]
    # each parent sees only their own child (a parent's "view progress" consent includes gaps, by design)
    p = login(client, "demo.parent@example.com")
    assert client.get(f"/progress/students/{riya}/history", headers=H(p)).status_code == 200
    assert client.get(f"/progress/students/{arjun}/history", headers=H(p)).status_code == 404
    p2 = login(client, "demo.parent2@example.com")
    assert client.get(f"/progress/students/{arjun}/history", headers=H(p2)).json()["started"]
    # a viewer without the gaps scope gets the same timeline without misconception names or Checker reasons
    from backend import db, history
    from backend.progress import _student_of
    with db.transaction() as c:
        h = history.student_history(c, _student_of(c, arjun), arjun, show_gaps=False)
    assert h["events"] and all(e["text"] == "Possible gap spotted" for e in h["events"] if e["kind"] == "suspected")
    assert all(e["detail"] is None for e in h["events"] if e["kind"] in ("confirmed", "rejected", "inconclusive"))
    assert not any(k["state"] == "working" for s in h["skill_map"] for t in s["topics"] for k in t["skills"])
    # a stranger and a student from another account can't see anyone's history
    stranger, _ = make_learner(client, email="someone@example.org")
    assert client.get(f"/progress/students/{riya}/history", headers=H(stranger)).status_code == 404
    k = login(client, "kabir.demo")
    assert client.get(f"/progress/students/{riya}/history", headers=H(k)).status_code in (403, 404)
    # the admin manages the school but doesn't read learning histories
    a = login(client, "demo.admin@example.com")
    assert client.get(f"/progress/students/{riya}/history", headers=H(a)).status_code in (403, 404)


def test_same_reference_date_gives_the_same_history():
    from backend import db, history
    from backend.progress import _student_of
    ref = date(2026, 11, 23)

    def snapshot():
        out = {}
        with db.transaction() as c:
            for slug in ("riya", "arjun", "kabir", "meera", "zoya"):
                uid = c.execute("SELECT ref_id FROM demo_registry WHERE slug=?", (slug,)).fetchone()[0]
                h = history.student_history(c, _student_of(c, uid), uid)
                out[slug] = ([(m["key"], m["answers"], m["correct"], m["mastered"]) for m in h["months"]],
                             [(e["date"], e["kind"], e["topic_id"]) for e in h["events"]])
        return out
    demo_script.seed(reference_date=ref, password=PW)
    a = snapshot()
    demo_script.reset(reference_date=ref, password=PW)
    b = snapshot()
    assert a == b
    assert db_one("SELECT COUNT(*) FROM demo_registry WHERE kind='user'")[0] == 13      # no duplicates after reset
