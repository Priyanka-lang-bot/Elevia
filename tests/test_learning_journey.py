"""The logged-in student journey (/learn): entry -> check-in -> double-check -> plan -> lesson -> retest -> replan.

Everything goes through the real HTTP routes and the real rule-based agents. Nothing is mocked except
the clock-free 'early retest' switch, which the app itself provides for demos.
"""
import json

import pytest

from backend import db
from backend.content import misconceptions, questions
from backend.fractions_engine import (answer_input_kind, check_answer, choices, correct_answer,
                                      correct_answer_text)
from tests.test_accounts import H, consent, db_one, make_child, make_learner

DIAG_WRONG = {"DA3": "2/5", "DA5": "3/7"}          # both: adds numerators and denominators
CD_CONFIRM = {"CD-V1": "2/9", "CD-V3": "10"}       # new questions, same kind of mistake -> confirmed
WRONG = "1/100"                                     # valid fraction, never correct


def right(qid):
    return correct_answer_text(questions()[qid])


@pytest.fixture
def me(client):
    token, user_id = make_learner(client)
    return H(token)


def state(client, h):
    r = client.get("/learn/state", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def start(client, h, grade=5):
    r = client.post("/learn/start", json={"grade": grade}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def answer(client, h, st, qid, text):
    r = client.post("/learn/answer", headers=h, json={
        "assessment_id": st["assessment"]["id"], "question_id": qid, "answer": text})
    assert r.status_code == 200, r.text
    return r.json()


def wrong_for(qid):
    """A valid answer that is never correct for this question."""
    q = questions()[qid]
    kind = answer_input_kind(q)
    if kind == "integer":
        return str(int(correct_answer(q)) + 1)
    if kind == "choice":
        return next(c for c in choices(q) if c != correct_answer_text(q))
    return WRONG


def answer_all(client, h, st, overrides=None, wrong=False):
    """Answer every open question: exact right answers by default, or all wrong with wrong=True."""
    out = None
    for q in st["assessment"]["questions"]:
        if q["answered"]:
            continue
        text = (overrides or {}).get(q["id"], wrong_for(q["id"]) if wrong else right(q["id"]))
        out = answer(client, h, st, q["id"], text)
        assert out["accepted"], out
    return out["state"]


def to_verification(client, h, wrong=DIAG_WRONG):
    st = start(client, h)
    assert st["phase"] == "checkin"
    st = answer_all(client, h, st, wrong)
    assert st["phase"] == "verify"
    return st


def to_learning(client, h):
    st = to_verification(client, h)
    st = answer_all(client, h, st, CD_CONFIRM)
    assert st["phase"] == "learn"
    return st


def practise_and_wait(client, h, st):
    """Do the practice set (right answers) and finish it; the retest is then scheduled for later."""
    st = answer_all(client, h, st)
    if st["phase"] == "learn":                       # practice not auto-completed: finish it explicitly
        r = client.post("/learn/practice/finish", json={"assessment_id": st["assessment"]["id"]}, headers=h)
        assert r.status_code == 200, r.text
        st = r.json()
    assert st["phase"] == "retest_wait"
    return st


def to_retest(client, h):
    st = practise_and_wait(client, h, to_learning(client, h))
    r = client.post("/learn/retest/start", json={"early": True}, headers=h)
    assert r.status_code == 200, r.text
    st = r.json()
    assert st["phase"] == "retest"
    return st


def count(sql, *args):
    return db_one(sql, *args)[0]


# ---------------------------------------------------------------- step 1: entry

def test_entry_needs_login_and_right_role(client):
    assert client.get("/learn/state").status_code == 401
    assert client.post("/learn/start", json={"grade": 5}).status_code == 401
    # a teacher/parent/admin has no learning area
    token, uid = make_learner(client, email="p@example.com")
    with db.transaction() as c:
        c.execute("UPDATE users SET role='parent' WHERE id=?", (uid,))
    assert client.get("/learn/state", headers=H(token)).status_code == 403


def test_entry_welcome_then_start_creates_one_session(client, me):
    st = state(client, me)
    assert st["phase"] == "welcome" and st["needs_grade"] is True and st["student"]["name"] == "Ada"
    assert [s["status"] for s in st["journey"]] == ["todo"] * 5
    # no grade -> clear message, nothing created
    assert client.post("/learn/start", json={}, headers=me).status_code == 400
    assert count("SELECT COUNT(*) FROM students") == 0
    # grade outside the fractions content is refused
    assert client.post("/learn/start", json={"grade": 12}, headers=me).status_code == 422

    st = start(client, me)
    again = start(client, me)                        # double click / second tab
    assert st["case_id"] == again["case_id"]
    assert count("SELECT COUNT(*) FROM students") == 1 and count("SELECT COUNT(*) FROM cases") == 1
    assert count("SELECT COUNT(*) FROM learner_links") == 1
    assert st["phase"] == "checkin" and st["assessment"]["total"] == 5
    assert st["journey"][0]["status"] == "current"


def test_child_student_can_enter_after_parent_consent(client):
    token, _ = make_child(client)
    assert client.get("/learn/state", headers=H(token)).status_code == 403   # not active until a parent says yes
    assert consent(client).status_code == 200
    st = client.get("/learn/state", headers=H(token)).json()
    assert st["phase"] == "welcome"


# ---------------------------------------------------------------- step 2-3: assessment and Diagnoser

def test_correct_initial_answers_close_with_no_gap(client, me):
    st = start(client, me)
    assert all("expected" not in q for q in st["assessment"]["questions"])      # answers never sent in advance
    out = None
    for q in st["assessment"]["questions"]:
        out = answer(client, me, st, q["id"], right(q["id"]))
        assert out["feedback"]["is_correct"] is True and out["feedback"]["message"] == "Correct."
    st = out["state"]
    assert st["phase"] == "done" and st["outcome"]["title"] == "No gap found"
    assert [s["status"] for s in st["journey"]] == ["done", "skipped", "skipped", "skipped", "done"]
    assert st["next_action"]["kind"] == "new_checkin"
    assert count("SELECT COUNT(*) FROM gaps") == 0 and count("SELECT COUNT(*) FROM plans") == 0
    assert {s["label"] for s in st["skills"] if s["attempts"]} == {"Getting there"}


def test_incorrect_answers_become_a_suspected_gap_and_nothing_is_planned(client, me):
    st = to_verification(client, me)
    assert st["gap"]["state"] == "checking" and "not confirmed" in st["gap"]["headline"].lower()
    assert st["testing_on"] == ["Finding common denominators"]
    assert st["assessment"]["total"] == 2
    assert count("SELECT COUNT(*) FROM plans") == 0 and count("SELECT COUNT(*) FROM lessons") == 0
    assert "lesson" not in st
    assert [s["status"] for s in st["journey"]][:2] == ["done", "current"]
    row = db_one("SELECT status, misconception FROM gaps")
    assert row["status"] == "suspected" and row["misconception"] in misconceptions()


def test_one_wrong_answer_is_offered_as_a_possible_slip(client, me):
    st = start(client, me)
    st = answer_all(client, me, st, {"DA3": "2/5"})
    assert st["phase"] == "verify"
    out = json.loads(db_one("SELECT output FROM agent_runs WHERE agent='Diagnoser'")[0])
    assert any(a["skill_name"] == "Careless slip" for a in out["alternatives"])
    assert out["primary"]["confidence_label"] != "high"
    # ...and a careless slip is cleared by the double-check, without any lesson being planned
    st = answer_all(client, me, st)
    assert st["phase"] == "done" and st["outcome"]["title"] == "It was a slip, not a gap"
    assert count("SELECT COUNT(*) FROM plans") == 0


# ---------------------------------------------------------------- step 4: Checker

def test_confirmed_gap_gets_planned_and_taught(client, me):
    st = to_learning(client, me)
    assert st["gap"]["state"] == "verified"
    assert st["lesson"]["title"] == "Finding common denominators"
    assert st["lesson"]["worked_examples"][0]["steps"] and st["lesson"]["steps"]
    assert "common denominators" in st["why_learning"].lower()
    assert st["assessment"]["kind"] == "practice" and st["assessment"]["total"] >= 4
    row = db_one("SELECT status, verified_by FROM gaps")
    assert (row["status"], row["verified_by"]) == ("confirmed", "Checker")
    assert count("SELECT COUNT(*) FROM plans WHERE status='active'") == 1
    assert db_one("SELECT source FROM lessons")[0] == "template"      # template fallback, no AI key needed
    # the verification questions were new
    diag = {r[0] for r in _qids("diagnostic")}
    ver = {r[0] for r in _qids("verification")}
    assert diag.isdisjoint(ver)


def _qids(kind):
    with db.transaction() as c:
        return [(q,) for a in c.execute("SELECT question_ids FROM assessments WHERE kind=?", (kind,)).fetchall()
                for q in json.loads(a["question_ids"])]


def test_rejected_gap_does_not_change_the_plan(client, me):
    st = to_verification(client, me)
    st = answer_all(client, me, st)                                  # both new questions right
    assert st["phase"] == "done" and st["outcome"]["title"] == "It was a slip, not a gap"
    assert db_one("SELECT status FROM gaps")[0] == "rejected"
    assert count("SELECT COUNT(*) FROM plans") == 0 and count("SELECT COUNT(*) FROM lessons") == 0
    assert [s["status"] for s in st["journey"]] == ["done", "done", "skipped", "skipped", "done"]


def test_inconclusive_verification_waits_for_a_teacher(client, me):
    st = to_verification(client, me, {"DA3": "2/5"})
    st = answer_all(client, me, st, {"CD-V1": "3/4"})                # one new mistake that isn't the pattern
    assert st["phase"] == "teacher_wait"
    assert db_one("SELECT status FROM gaps")[0] == "inconclusive"
    assert count("SELECT COUNT(*) FROM plans") == 0                  # unverified gaps are never planned
    assert "will not guess" in st["why"]
    assert st["gap"]["state"] == "unclear"


# ---------------------------------------------------------------- steps 6-8: Tutor, retest, replanning

def test_practice_has_hints_and_full_feedback_but_does_not_change_mastery(client, me):
    st = to_learning(client, me)
    a = st["assessment"]
    q = a["questions"][0]
    h = client.get("/learn/hint", params={"assessment_id": a["id"], "question_id": q["id"], "level": 1}, headers=me)
    assert h.status_code == 200 and h.json()["hint"]
    out = answer(client, me, st, q["id"], wrong_for(q["id"]))
    assert out["feedback"]["expected"] and out["feedback"]["solution"]     # practice shows the worked solution
    assert db_one("SELECT status FROM skill_mastery WHERE skill_id='common_denominators'")[0] == "needs_practice"
    # too early to finish
    r = client.post("/learn/practice/finish", json={"assessment_id": a["id"]}, headers=me)
    assert r.status_code == 400


def test_retest_is_locked_until_the_delay_then_unlocked_for_demo(client, me, monkeypatch):
    st = practise_and_wait(client, me, to_learning(client, me))
    assert st["retest"]["unlocked"] is False and st["retest"]["seconds_left"] > 23 * 3600
    assert st["retest"]["can_start_early"] is True
    assert client.post("/learn/retest/start", json={"early": False}, headers=me).status_code == 409
    monkeypatch.setenv("ALLOW_EARLY_RETEST", "false")
    assert client.post("/learn/retest/start", json={"early": True}, headers=me).status_code == 403
    assert client.get("/learn/state", headers=me).json()["retest"]["can_start_early"] is False
    # after the delay the student can start without any override
    with db.transaction() as c:
        c.execute("UPDATE assessments SET available_at='2000-01-01T00:00:00+00:00' WHERE kind='retest'")
    st = client.post("/learn/retest/start", json={"early": False}, headers=me).json()
    assert st["phase"] == "retest" and st["assessment"]["total"] == 3
    # double click is harmless
    assert client.post("/learn/retest/start", json={"early": False}, headers=me).json()["phase"] == "retest"


def test_successful_retest_records_mastery(client, me):
    st = to_retest(client, me)
    ids = [q["id"] for q in st["assessment"]["questions"]]
    seen = {q for kind in ("diagnostic", "verification", "practice") for (q,) in _qids(kind)}
    assert not seen & set(ids)                                        # retest never repeats earlier questions
    # 2 of 3 is enough
    st = answer_all(client, me, st, {ids[0]: wrong_for(ids[0])})
    assert st["phase"] == "done" and st["outcome"]["title"] == "Gap closed"
    assert st["outcome"]["retest"]["passed"] is True and st["outcome"]["retest"]["score"]["correct"] == 2
    assert st["gap"]["state"] == "resolved"
    assert [s["status"] for s in st["journey"]] == ["done"] * 5
    assert db_one("SELECT status FROM gaps")[0] == "resolved"
    assert db_one("SELECT status FROM skill_mastery WHERE skill_id='common_denominators'")[0] == "mastered"
    assert db_one("SELECT status FROM plans")[0] == "completed"
    assert st["next_action"]["kind"] == "new_checkin"


def test_failed_retest_keeps_the_gap_open_and_replans(client, me):
    st = to_retest(client, me)
    first_retest = [q["id"] for q in st["assessment"]["questions"]]
    ids = first_retest
    st = answer_all(client, me, st, {ids[0]: right(ids[0])}, wrong=True)     # 1 of 3
    assert st["phase"] == "learn" and st["round"] == 2
    assert st["gap"]["state"] == "still_present"
    assert st["previous_retest"]["passed"] is False and st["previous_retest"]["score"]["correct"] == 1
    assert db_one("SELECT status FROM gaps")[0] == "still_present"
    assert db_one("SELECT status FROM skill_mastery WHERE skill_id='common_denominators'")[0] != "mastered"
    # a new plan and a new lesson were produced, the old plan was replaced
    assert count("SELECT COUNT(*) FROM plans") == 2 and count("SELECT COUNT(*) FROM plans WHERE status='active'") == 1
    assert count("SELECT COUNT(*) FROM lessons") == 2
    assert "retest showed" in st["why_learning"].lower()
    assert st["lesson"] and st["assessment"]["kind"] == "practice"

    # second cycle: practice -> a NEW retest -> pass
    st = practise_and_wait(client, me, st)
    st = client.post("/learn/retest/start", json={"early": True}, headers=me).json()
    second = [q["id"] for q in st["assessment"]["questions"]]
    assert not set(second) & set(first_retest)
    st = answer_all(client, me, st)
    assert st["phase"] == "done" and st["outcome"]["title"] == "Gap closed"
    assert db_one("SELECT status FROM skill_mastery WHERE skill_id='common_denominators'")[0] == "mastered"
    assert count("SELECT COUNT(*) FROM gaps WHERE status='resolved'") == 1


def test_every_skill_can_fail_one_retest_and_still_get_a_new_one():
    """Replanning needs fresh questions: each teachable skill must have at least two retest sets."""
    from backend.agents.checker import N_RETEST
    from backend.content import lessons, questions_in_pool
    for skill in lessons():
        assert len(questions_in_pool(f"retest:{skill}")) >= 2 * N_RETEST, skill


# ---------------------------------------------------------------- persistence

def test_progress_persists_across_logins_and_reloads(client, me):
    st = start(client, me)
    q1, q2 = st["assessment"]["questions"][:2]
    answer(client, me, st, q1["id"], right(q1["id"]))
    answer(client, me, st, q2["id"], wrong_for(q2["id"]))
    # a brand-new session for the same account (new login) sees exactly the same place
    t = client.post("/auth/login", json={"identifier": "ada@example.com", "password": "Correct-horse-42"}).json()["token"]
    st2 = state(client, H(t))
    assert st2["phase"] == "checkin" and st2["case_id"] == st["case_id"]
    assert st2["assessment"]["answered"] == 2
    done = {q["id"]: q for q in st2["assessment"]["questions"] if q["answered"]}
    assert done[q1["id"]]["is_correct"] is True and done[q2["id"]]["is_correct"] is False
    assert st2["assessment"]["questions"][2]["answered"] is False
    # ...and answers are stored with the attempt data
    row = db_one("SELECT answer_raw, is_correct, hints_used FROM responses WHERE question_id=?", q2["id"])
    assert (row["answer_raw"], row["is_correct"]) == (wrong_for(q2["id"]), 0)


def test_finished_rounds_are_listed_and_a_new_round_uses_the_other_question_set(client, me):
    st = start(client, me)
    st = answer_all(client, me, st)
    assert st["phase"] == "done" and len(st["rounds"]) == 1
    first_ids = {q["id"] for q in _all_questions(st)}
    st = start(client, me)                                            # next action: new check-in
    assert st["phase"] == "checkin" and len(st["rounds"]) == 2
    assert st["assessment"]["questions"][0]["id"] not in first_ids
    assert count("SELECT COUNT(*) FROM students") == 1


def _all_questions(st):
    return [{"id": qid} for (qid,) in _qids("diagnostic")][:5]


def test_two_students_never_see_each_other(client, me):
    st = start(client, me)
    other_token, _ = make_learner(client, email="bo@example.com")
    ho = H(other_token)
    assert state(client, ho)["phase"] == "welcome"
    r = client.post("/learn/answer", headers=ho, json={
        "assessment_id": st["assessment"]["id"], "question_id": st["assessment"]["questions"][0]["id"], "answer": "1"})
    assert r.status_code in (404, 409)                                # not found / no session; never recorded
    assert count("SELECT COUNT(*) FROM responses") == 0
    start(client, ho)
    r = client.post("/learn/answer", headers=ho, json={
        "assessment_id": st["assessment"]["id"], "question_id": st["assessment"]["questions"][0]["id"], "answer": "1"})
    assert r.status_code == 404
    assert client.get("/learn/hint", params={"assessment_id": st["assessment"]["id"], "question_id": "DA1"},
                      headers=ho).status_code == 404
    assert count("SELECT COUNT(*) FROM responses") == 0


# ---------------------------------------------------------------- errors and duplicates

def test_duplicate_submission_is_recorded_once(client, me):
    st = start(client, me)
    q = st["assessment"]["questions"][0]
    first = answer(client, me, st, q["id"], right(q["id"]))
    again = answer(client, me, st, q["id"], right(q["id"]))
    assert first["duplicate"] is False and again["duplicate"] is True and again["is_correct"] is True
    assert count("SELECT COUNT(*) FROM responses") == 1
    # an equivalent way of writing the same answer is also the same submission
    r = client.post("/learn/answer", headers=me, json={"assessment_id": st["assessment"]["id"],
                                                        "question_id": q["id"], "answer": " " + right(q["id"]) + " "})
    assert r.json()["duplicate"] is True
    # a DIFFERENT answer for an answered question is refused, the first one stands
    r = client.post("/learn/answer", headers=me, json={"assessment_id": st["assessment"]["id"],
                                                        "question_id": q["id"], "answer": WRONG})
    assert r.status_code == 409
    assert db_one("SELECT is_correct FROM responses")[0] == 1


def test_bad_input_is_explained_and_not_recorded(client, me):
    st = start(client, me)
    q = st["assessment"]["questions"][0]
    for bad in ("", "abc", "1/0", "0.5", "3//4"):
        r = client.post("/learn/answer", headers=me, json={"assessment_id": st["assessment"]["id"],
                                                            "question_id": q["id"], "answer": bad})
        assert r.status_code == 200 and r.json()["accepted"] is False and r.json()["error"], bad
    assert count("SELECT COUNT(*) FROM responses") == 0
    # wrong question for this set / over-long text / missing session
    assert client.post("/learn/answer", headers=me, json={"assessment_id": st["assessment"]["id"],
                                                          "question_id": "CD-R1", "answer": "1"}).status_code == 400
    assert client.post("/learn/answer", headers=me, json={"assessment_id": st["assessment"]["id"],
                                                          "question_id": q["id"], "answer": "9" * 41}).status_code == 422
    assert client.post("/learn/answer", headers=me, json={"assessment_id": 99999, "question_id": q["id"],
                                                          "answer": "1"}).status_code == 404


def test_answering_a_finished_assessment_is_refused_without_changing_anything(client, me):
    st = start(client, me)
    aid, qs = st["assessment"]["id"], [q["id"] for q in st["assessment"]["questions"]]
    answer_all(client, me, st)
    before = count("SELECT COUNT(*) FROM responses")
    r = client.post("/learn/answer", headers=me, json={"assessment_id": aid, "question_id": qs[0], "answer": WRONG})
    assert r.status_code == 409
    assert count("SELECT COUNT(*) FROM responses") == before


def test_a_crash_while_checking_answers_keeps_the_answers(client, me, monkeypatch):
    from backend.agents import diagnoser

    def boom(payload):
        raise RuntimeError("simulated failure")
    monkeypatch.setattr(diagnoser, "run", boom)
    st = start(client, me)
    st = answer_all(client, me, st, DIAG_WRONG)
    assert st["phase"] == "teacher_wait" and "Your answers are saved" in st["why"]
    assert count("SELECT COUNT(*) FROM responses") == 5               # nothing lost
    assert count("SELECT COUNT(*) FROM plans") == 0
    assert db_one("SELECT status FROM assessments WHERE kind='diagnostic'")[0] == "completed"


def test_retest_start_without_a_waiting_retest_is_an_error(client, me):
    assert client.post("/learn/retest/start", json={"early": True}, headers=me).status_code == 409
    start(client, me)
    assert client.post("/learn/retest/start", json={"early": True}, headers=me).status_code == 409


def test_student_view_never_leaks_internals(client, me):
    st = to_learning(client, me)
    blob = json.dumps(st)
    for word in ("agent_runs", "confidence", "Diagnoser", "Checker", "Planner", "Tutor", "verified_by", "pattern",
                 "evidence", *misconceptions().keys()):
        assert word not in blob, word


# ---------------------------------------------------------------- exact maths (the one place correctness is decided)

@pytest.mark.parametrize("qtype,a,b,answer,ok", [
    ("add", "1/2", "1/3", "5/6", True),
    ("add", "1/2", "1/3", "10/12", True),       # equivalent, not simplified: still correct for addition
    ("add", "1/2", "1/3", "2/5", False),        # the classic mistake
    ("add", "1/3", "1/3", "2/3", True),
    ("add", "3/4", "3/4", "1 1/2", True),       # mixed number
    ("add", "3/4", "3/4", "3/2", True),
    ("sub", "3/4", "1/3", "5/12", True),
    ("multiply", "2/3", "3/5", "6/15", True),
    ("multiply", "2/3", "3/5", "2/5", True),
    ("multiply", "2/3", "3/5", "5/8", False),
])
def test_exact_checking_uses_fractions_not_floats(qtype, a, b, answer, ok):
    q = {"id": "t", "pool": "t", "skill_id": "add_sub_unlike", "type": qtype, "gap_targets": [], "a": a, "b": b}
    res = check_answer(q, answer)
    assert res.valid and res.correct is ok


def test_simplify_requires_lowest_terms_and_decimals_are_not_guessed():
    q = {"id": "t", "pool": "t", "skill_id": "simplifying_fractions", "type": "simplify", "gap_targets": [], "a": "6/8"}
    assert check_answer(q, "3/4").correct
    assert not check_answer(q, "6/8").correct          # same value, not simplified
    assert not check_answer(q, "9/12").correct
    assert not check_answer(q, "0.75").valid           # no float guessing
    assert not check_answer(q, "1/0").valid
    # 1/3 as a decimal would be inexact; exact arithmetic never rounds
    q2 = {"id": "t", "pool": "t", "skill_id": "add_sub_unlike", "type": "add", "gap_targets": [], "a": "1/3", "b": "1/3"}
    assert check_answer(q2, "2/3").correct and not check_answer(q2, "0.6667").valid


def test_whole_bank_answers_are_computed_and_accepted():
    for q in questions().values():
        res = check_answer(q, correct_answer_text(q))
        assert res.valid and res.correct, q["id"]
