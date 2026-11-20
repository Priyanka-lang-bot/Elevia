"""Teacher / parent / shared progress views and teacher gap review, with permission isolation."""
from backend.content import questions
from backend.engine import correct_answer_text
from tests.test_accounts import (H, add_teacher, consent, db_one, last_link_token, make_child, make_learner,
                                 school_student, setup_school)


def enrolled_student(client):
    """School student in class 7B, parent consented with progress, approved by teacher T1."""
    _, admin, class_id = setup_school(client)
    t1, _ = add_teacher(client, admin, class_id, "asha@sunrise.in")
    other_class = client.post("/school/classes", json={"grade": 8, "division": "A", "academic_year": "2026-27"},
                              headers=H(admin)).json()["id"]
    t2, _ = add_teacher(client, admin, other_class, "ben@sunrise.in")
    code = client.post("/school/codes", json={"class_id": class_id}, headers=H(admin)).json()["code"]
    r = school_student(client, code)
    s_token, s_id = r.json()["token"], r.json()["user"]["id"]
    parent = consent(client, "papa@example.com", full_name="Raj Patel").json()["token"]
    enr = client.get(f"/school/classes/{class_id}/roster", headers=H(t1)).json()["students"][0]
    client.post(f"/school/enrollments/{enr['enrollment_id']}/approve", headers=H(t1))
    return {"admin": admin, "t1": t1, "t2": t2, "student": s_token, "sid": s_id, "parent": parent}


def answer_all(client, h, st, answers=None):
    out = None
    for q in st["assessment"]["questions"]:
        if not q["answered"]:
            out = client.post("/learn/answer", headers=h, json={
                "assessment_id": st["assessment"]["id"], "question_id": q["id"],
                "answer": (answers or {}).get(q["id"], correct_answer_text(questions()[q["id"]]))}).json()
    return out["state"]


def to_inconclusive(client, h):
    st = client.post("/learn/start", json={"grade": 7}, headers=h).json()
    st = answer_all(client, h, st, {"DA3": "2/5"})
    st = answer_all(client, h, st, {"CD-V1": "3/4"})
    assert st["phase"] == "teacher_wait"
    return st


def test_teacher_sees_class_progress_and_resolves_inconclusive_gap(client):
    s = enrolled_student(client)
    lst = client.get("/progress/students", headers=H(s["t1"])).json()
    grp = lst["groups"][0]
    assert grp["label"].startswith("Class 7 B") and grp["students"][0]["started"] is False   # honest empty state
    to_inconclusive(client, H(s["student"]))

    grp = client.get("/progress/students", headers=H(s["t1"])).json()["groups"][0]
    row = grp["students"][0]
    assert row["needs_review"] == 1 and row["answers"] == 7 and grp["insights"]["needs_review"] == 1
    d = client.get(f"/progress/students/{s['sid']}", headers=H(s["t1"])).json()
    assert d["can_review"] is True and d["access_via"] == "teacher_class"
    rnd = d["topics"][0]["rounds"][0]
    assert rnd["gap"]["status"] == "inconclusive" and rnd["gap"]["misconception"] and rnd["gap"]["evidence"]
    assert rnd["actions"]["decide"] is True and rnd["assessments"]

    # a reason is required
    bad = client.post(f"/progress/cases/{rnd['case_id']}/decision", json={"decision": "confirm", "reason": "ok"},
                      headers=H(s["t1"]))
    assert bad.status_code == 422
    ok = client.post(f"/progress/cases/{rnd['case_id']}/decision",
                     json={"decision": "confirm", "reason": "Saw this in class too"}, headers=H(s["t1"]))
    assert ok.status_code == 200 and ok.json()["stage"] == "learning"
    st = client.get("/learn/state", headers=H(s["student"])).json()
    assert st["phase"] == "learn" and "teacher" in st["why_learning"].lower() and st["gap"]["state"] == "verified"
    assert db_one("SELECT action FROM teacher_overrides")[0] == "confirm_gap"
    assert "Saw this" in db_one("SELECT reason FROM teacher_overrides")[0]
    # the override shows in the teacher's view
    d = client.get(f"/progress/students/{s['sid']}", headers=H(s["t1"])).json()
    assert d["topics"][0]["rounds"][0]["overrides"][0]["action"] == "confirm_gap"
    assert db_one("SELECT COUNT(*) FROM access_log WHERE what='progress'")[0] >= 1      # reads are logged


def test_teacher_can_reject_and_add_notes(client):
    s = enrolled_student(client)
    to_inconclusive(client, H(s["student"]))
    cid = db_one("SELECT id FROM cases")[0]
    assert client.post(f"/progress/cases/{cid}/note", json={"note": "Talk to Aarav on Monday"},
                       headers=H(s["t1"])).status_code == 200
    r = client.post(f"/progress/cases/{cid}/decision", json={"decision": "reject", "reason": "Just rushed it"},
                    headers=H(s["t1"]))
    assert r.json()["stage"] == "closed"
    st = client.get("/learn/state", headers=H(s["student"])).json()
    assert st["phase"] == "done" and st["outcome"]["title"] == "Your teacher reviewed this"


def test_other_teacher_admin_and_strangers_are_blocked(client):
    s = enrolled_student(client)
    to_inconclusive(client, H(s["student"]))
    cid = db_one("SELECT id FROM cases")[0]
    assert client.get("/progress/students", headers=H(s["t2"])).json()["groups"] == []
    assert client.get(f"/progress/students/{s['sid']}", headers=H(s["t2"])).status_code == 404
    assert client.post(f"/progress/cases/{cid}/decision", json={"decision": "reject", "reason": "not mine at all"},
                       headers=H(s["t2"])).status_code == 404
    assert client.get(f"/progress/students/{s['sid']}", headers=H(s["admin"])).status_code == 404   # admin: roster only
    stranger, _ = make_learner(client, "x@example.com")
    assert client.get(f"/progress/students/{s['sid']}", headers=H(stranger)).status_code == 404
    assert client.post(f"/progress/cases/{cid}/decision", json={"decision": "reject", "reason": "nope nope"},
                       headers=H(stranger)).status_code == 403
    # the student can't override their own gap
    assert client.post(f"/progress/cases/{cid}/decision", json={"decision": "reject", "reason": "I'm fine thanks"},
                       headers=H(s["student"])).status_code == 403
    assert db_one("SELECT COUNT(*) FROM teacher_overrides")[0] == 0


def test_parent_sees_progress_only_with_permission_and_cannot_override(client):
    s = enrolled_student(client)
    to_inconclusive(client, H(s["student"]))
    lst = client.get("/progress/students", headers=H(s["parent"])).json()
    assert lst["groups"][0]["label"] == "Your children" and lst["groups"][0]["insights"] is None
    d = client.get(f"/progress/students/{s['sid']}", headers=H(s["parent"])).json()
    assert d["can_review"] is False and "actions" not in d["topics"][0]["rounds"][0]
    cid = db_one("SELECT id FROM cases")[0]
    assert client.post(f"/progress/cases/{cid}/decision", json={"decision": "reject", "reason": "my child is fine"},
                       headers=H(s["parent"])).status_code == 403
    # a parent who only allowed 'view_activity' sees nothing
    _, kid = make_child(client, "kid_q", "dad2@example.com")
    p2 = consent(client, "dad2@example.com", perms=("view_activity",), full_name="Dad Two").json()["token"]
    assert client.get("/progress/students", headers=H(p2)).json()["groups"] == []
    assert client.get(f"/progress/students/{kid}", headers=H(p2)).status_code == 404


def test_learner_shares_progress_with_a_mentor(client):
    l_token, l_id = make_learner(client)
    client.post("/learn/start", json={"grade": 9, "topic_id": "loops"}, headers=H(l_token))
    _, _ = make_child(client, "kid_m", "mentor@example.com")
    mentor = consent(client, "mentor@example.com", full_name="Mentor Mehta").json()["token"]
    assert client.get("/progress/students", headers=H(mentor)).json()["groups"][0]["label"] == "Your children"
    client.post("/sharing/invite", json={"email": "mentor@example.com", "scopes": ["progress"]}, headers=H(l_token))
    client.post("/sharing/accept", json={"token": last_link_token("mentor@example.com")}, headers=H(mentor))
    groups = {g["label"]: g for g in client.get("/progress/students", headers=H(mentor)).json()["groups"]}
    shared = groups["Shared with you"]["students"][0]
    assert shared["name"] == "Ada Learner" and shared["active"][0]["topic"] == "Loops"
    d = client.get(f"/progress/students/{l_id}", headers=H(mentor)).json()
    assert d["can_see_gaps"] is False and "gap" not in d["topics"][0]["rounds"][0]   # only what was shared
