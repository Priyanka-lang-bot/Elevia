"""End-to-end tests through the FastAPI routes (the same routes the Streamlit UI uses)."""
import sqlite3

from backend.content import questions
from backend.fractions_engine import correct_answer_text
from tests.conftest import TEACHER


def right(qid):
    return correct_answer_text(questions()[qid])


def new_student(client, name="Test"):
    r = client.post("/students", json={"display_name": name, "grade": 5})
    assert r.status_code == 201
    return r.json()["id"]


def answer_all(client, case, answers=None):
    a = case["open_assessment"]
    data = None
    for q in a["questions"]:
        if q["answered"]:
            continue
        r = client.post(f"/assessments/{a['id']}/answers",
                        json={"question_id": q["id"], "answer": (answers or {}).get(q["id"], right(q["id"]))})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["accepted"], data
    return data["case"]


DIAG_WRONG = {"DA3": "2/5", "DA5": "3/7"}


def test_full_demo_workflow(client):
    sid = new_student(client)
    case = client.post(f"/students/{sid}/cases").json()
    assert case["stage"] == "diagnostic" and case["open_assessment"]["total"] == 5

    # student never sees answers during assessment
    assert all("expected" not in q for q in case["open_assessment"]["questions"])

    case = answer_all(client, case, DIAG_WRONG)
    assert case["stage"] == "verification"
    assert case["gap"]["status"] == "suspected" and case["gap"]["skill_id"] == "common_denominators"
    assert case["plan"] is None  # unverified gap must not create a plan
    assert case["open_assessment"]["total"] == 2

    case = answer_all(client, case, {"CD-V1": "2/9", "CD-V3": "10"})
    assert case["stage"] == "learning"
    assert case["gap"]["status"] == "confirmed" and case["gap"]["verified_by"] == "Checker"
    assert case["plan"]["focus_skill"] == "common_denominators"
    assert case["lesson"]["source"] == "template"
    agents = [(r["agent"], r["step"], r["status"]) for r in case["agent_runs"]]
    assert agents == [("Diagnoser", "diagnose", "succeeded"), ("Checker", "select_verification", "succeeded"),
                      ("Checker", "evaluate_verification", "succeeded"), ("Planner", "plan", "succeeded"),
                      ("Tutor", "teach", "succeeded")]

    # practice + hints
    pa = case["open_assessment"]
    assert pa["kind"] == "practice"
    h = client.get(f"/assessments/{pa['id']}/hint", params={"question_id": pa["questions"][0]["id"], "level": 1})
    assert h.status_code == 200 and h.json()["agent"] == "Tutor"
    r = client.post(f"/assessments/{pa['id']}/answers", json={"question_id": pa["questions"][0]["id"], "answer": "7"})
    body = r.json()
    assert body["is_correct"] is False and body["expected"] and body["solution"]
    client.post(f"/assessments/{pa['id']}/answers", json={"question_id": pa["questions"][1]["id"],
                                                          "answer": right(pa["questions"][1]["id"])})
    case = client.post(f"/assessments/{pa['id']}/finish").json()
    assert case["stage"] == "retest_pending"

    # retest locked until tomorrow, demo override allowed and logged
    assert client.post(f"/cases/{case['id']}/retest", json={"early": False}).status_code == 409
    case = client.post(f"/cases/{case['id']}/retest", json={"early": True}).json()
    assert case["stage"] == "retest"
    assert any(r["step"] == "early_retest_override" for r in case["agent_runs"])

    case = answer_all(client, case)
    assert case["stage"] == "completed" and case["gap"]["status"] == "resolved"

    ov = client.get(f"/students/{sid}/overview").json()
    assert ov["improvements"][0]["verification_rate"] == 0.0
    assert ov["improvements"][0]["retest_rate"] == 1.0
    skills = {s["skill_id"]: s["status"] for s in ov["skills"]}
    assert skills["common_denominators"] == "mastered"
    assert ov["totals"]["practice"]["attempted"] == 2


def test_failed_retest_replans(client):
    sid = new_student(client)
    case = client.post(f"/students/{sid}/cases").json()
    case = answer_all(client, case, DIAG_WRONG)
    case = answer_all(client, case, {"CD-V1": "2/9", "CD-V3": "10"})
    pa = case["open_assessment"]
    for q in pa["questions"][:2]:
        client.post(f"/assessments/{pa['id']}/answers", json={"question_id": q["id"], "answer": right(q["id"])})
    case = client.post(f"/assessments/{pa['id']}/finish").json()
    case = client.post(f"/cases/{case['id']}/retest", json={"early": True}).json()
    wrong = {q["id"]: "1/99" for q in case["open_assessment"]["questions"]}
    case = answer_all(client, case, wrong)
    assert case["gap"]["status"] == "still_present"
    assert case["stage"] == "learning"  # Planner and Tutor ran again
    assert [r["step"] for r in case["agent_runs"]].count("plan") == 2


def test_no_gap_when_all_correct(client):
    sid = new_student(client)
    case = answer_all(client, client.post(f"/students/{sid}/cases").json())
    assert case["stage"] == "closed" and case["closed_reason"] == "no_gap_found" and case["gap"] is None


def test_unconfirmed_gap_does_not_change_plan(client):
    sid = new_student(client)
    case = answer_all(client, client.post(f"/students/{sid}/cases").json(), DIAG_WRONG)
    case = answer_all(client, case)  # verification all correct
    assert case["gap"]["status"] == "rejected"
    assert case["stage"] == "closed" and case["plan"] is None and case["lesson"] is None


def test_inconclusive_goes_to_teacher_then_override(client):
    sid = new_student(client)
    case = answer_all(client, client.post(f"/students/{sid}/cases").json(), {"DA3": "2/5"})
    case = answer_all(client, case, {"CD-V1": "3/4"})
    assert case["stage"] == "teacher_review" and case["gap"]["status"] == "inconclusive" and case["plan"] is None

    # teacher endpoints need the PIN
    assert client.get("/teacher/overview").status_code == 401
    assert client.get("/teacher/overview", headers={"X-Teacher-Pin": "wrong"}).status_code == 401
    rows = client.get("/teacher/overview", headers=TEACHER).json()
    assert rows[0]["needs_review"]

    # reason is required
    r = client.post(f"/teacher/cases/{case['id']}/gap-decision", headers=TEACHER,
                    json={"decision": "confirm", "teacher_name": "Ms Rao", "reason": ""})
    assert r.status_code == 422

    r = client.post(f"/teacher/cases/{case['id']}/gap-decision", headers=TEACHER,
                    json={"decision": "confirm", "teacher_name": "Ms Rao", "reason": "Saw this in class too."})
    case = r.json()
    assert case["stage"] == "learning" and case["gap"]["verified_by"] == "teacher:Ms Rao"
    assert case["plan"]["created_by"] == "teacher:Ms Rao"

    r = client.post(f"/teacher/cases/{case['id']}/focus", headers=TEACHER,
                    json={"focus_skill": "equivalent_fractions", "teacher_name": "Ms Rao",
                          "reason": "Start one step earlier."})
    case = r.json()
    assert case["plan"]["focus_skill"] == "equivalent_fractions"
    assert case["lesson"]["skill_id"] == "equivalent_fractions"
    assert [o["action"] for o in case["overrides"]] == ["confirm_gap", "change_focus"]


def test_teacher_reject_closes_case(client):
    sid = new_student(client)
    case = answer_all(client, client.post(f"/students/{sid}/cases").json(), DIAG_WRONG)
    case = answer_all(client, case, {"CD-V1": "2/9", "CD-V3": "10"})
    r = client.post(f"/teacher/cases/{case['id']}/gap-decision", headers=TEACHER,
                    json={"decision": "reject", "teacher_name": "Mr K", "reason": "Rushed the test, knows this."})
    case = r.json()
    assert case["stage"] == "closed" and case["gap"]["status"] == "rejected"
    assert case["plan"]["status"] == "cancelled"


def test_override_blocked_during_verification(client):
    sid = new_student(client)
    case = answer_all(client, client.post(f"/students/{sid}/cases").json(), DIAG_WRONG)
    r = client.post(f"/teacher/cases/{case['id']}/gap-decision", headers=TEACHER,
                    json={"decision": "confirm", "teacher_name": "Mr K", "reason": "trying early"})
    assert r.status_code == 409


def test_input_validation(client):
    assert client.post("/students", json={"display_name": "", "grade": 5}).status_code == 422
    assert client.post("/students", json={"display_name": "A", "grade": 12}).status_code == 422
    sid = new_student(client)
    case = client.post(f"/students/{sid}/cases").json()
    a = case["open_assessment"]
    r = client.post(f"/assessments/{a['id']}/answers", json={"question_id": "DA3", "answer": "banana"})
    assert r.status_code == 200 and r.json()["accepted"] is False
    client.post(f"/assessments/{a['id']}/answers", json={"question_id": "DA3", "answer": "5/6"})
    assert client.post(f"/assessments/{a['id']}/answers", json={"question_id": "DA3", "answer": "5/6"}).status_code == 409
    assert client.post(f"/assessments/{a['id']}/answers", json={"question_id": "CD-V1", "answer": "1/2"}).status_code == 400
    assert client.get(f"/assessments/{a['id']}/hint", params={"question_id": "DA1"}).status_code == 403
    assert client.get("/cases/9999").status_code == 404
    # starting again returns the same active case
    assert client.post(f"/students/{sid}/cases").json()["id"] == case["id"]


def test_early_retest_can_be_disabled(client, monkeypatch):
    sid = new_student(client)
    case = answer_all(client, client.post(f"/students/{sid}/cases").json(), DIAG_WRONG)
    case = answer_all(client, case, {"CD-V1": "2/9", "CD-V3": "10"})
    pa = case["open_assessment"]
    for q in pa["questions"][:2]:
        client.post(f"/assessments/{pa['id']}/answers", json={"question_id": q["id"], "answer": right(q["id"])})
    case = client.post(f"/assessments/{pa['id']}/finish").json()
    monkeypatch.setenv("ALLOW_EARLY_RETEST", "false")
    assert client.post(f"/cases/{case['id']}/retest", json={"early": True}).status_code == 403


def test_records_persist_in_sqlite(client, tmp_path):
    sid = new_student(client, "Persist")
    case = answer_all(client, client.post(f"/students/{sid}/cases").json(), DIAG_WRONG)
    conn = sqlite3.connect(str(tmp_path / "test.db"))  # separate connection = what a restart would see
    assert conn.execute("SELECT display_name FROM students WHERE id=?", (sid,)).fetchone()[0] == "Persist"
    assert conn.execute("SELECT COUNT(*) FROM responses WHERE student_id=?", (sid,)).fetchone()[0] == 5
    assert conn.execute("SELECT status FROM gaps WHERE case_id=?", (case["id"],)).fetchone()[0] == "suspected"
    assert conn.execute("SELECT COUNT(*) FROM agent_runs WHERE case_id=?", (case["id"],)).fetchone()[0] == 2


def test_health_reports_mock_mode(client):
    h = client.get("/health").json()
    assert h["llm"]["mode"] == "mock" and h["ok"] and h["demo_teacher_pin"] is False
