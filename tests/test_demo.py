"""Demo mode: one-click login only for registry-listed demo accounts, safe reset, realistic consistent data."""
import importlib.util
from pathlib import Path

import pytest

from tests.test_accounts import H, db_one, make_learner

spec = importlib.util.spec_from_file_location("demo_script", Path(__file__).resolve().parent.parent / "scripts" / "demo.py")
demo_script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo_script)


PW = "Test-Demo-Pass-42"          # tests choose the demo password; real seeds generate one or read ELEVIA_DEMO_PASSWORD


def seed(**kw):
    kw.setdefault("password", PW)
    return demo_script.seed(**kw)


def count(sql, *a):
    return db_one(sql, *a)[0]


def demo_login(client, slug):
    r = client.post("/demo/login", json={"slug": slug}, headers={"X-Elevia-Web": "1"})
    return r


STAFF_LOGIN = {"teacher": "demo.teacher@example.com", "parent": "demo.parent@example.com",
               "admin": "demo.admin@example.com"}


def staff_login(client, slug):
    """Teacher/parent/admin demo accounts are not one-click: they log in with the normal password route."""
    return client.post("/auth/login", json={"identifier": STAFF_LOGIN[slug], "password": PW},
                       headers={"X-Elevia-Web": "1"})


@pytest.fixture
def demo_on(monkeypatch):
    monkeypatch.setenv("ELEVIA_DEMO_MODE", "1")


def test_demo_mode_is_off_by_default(client):
    seed()
    assert client.get("/demo/accounts").json() == {"enabled": False, "accounts": []}
    assert demo_login(client, "riya").status_code == 404


def test_not_ready_until_seeded(client, demo_on):
    d = client.get("/demo/accounts").json()
    assert d["enabled"] and not d["ready"] and not any(a["available"] for a in d["accounts"])
    assert demo_login(client, "riya").status_code == 409


def test_one_click_login_gives_a_normal_session_for_each_student(client, demo_on):
    seed()
    d = client.get("/demo/accounts").json()
    assert d["ready"] and {a["slug"] for a in d["accounts"]} == {"riya", "arjun", "fresh"}   # students only
    assert "Demo-Pass" not in str(d) and "password" not in str(d).lower()          # no credentials in the page
    roles = {"riya": "student", "arjun": "student", "fresh": "learner"}
    for slug, role in roles.items():
        r = demo_login(client, slug)
        assert r.status_code == 200, r.text
        assert "token" not in r.json()                                               # web clients never see it
        cookie = r.headers["set-cookie"].lower()
        assert "httponly" in cookie and "samesite=lax" in cookie
        tok = r.cookies.get("elevia_session") or cookie.split("elevia_session=")[1].split(";")[0]
        me = client.get("/auth/me", headers=H(tok)).json()
        assert me["user"]["role"] == role
    assert demo_login(client, "nobody").status_code == 400


def test_parent_and_admin_demo_accounts_are_never_one_click(client, demo_on, monkeypatch):
    monkeypatch.setenv("ELEVIA_DEMO_TEACHER_CODE", "judges-2026-code")
    seed(activity=False)
    for slug in ("parent", "parent2", "parent5", "admin"):
        r = client.post("/demo/login", json={"slug": slug, "access_code": "judges-2026-code"},
                        headers={"X-Elevia-Web": "1"})
        assert r.status_code == 403 and "set-cookie" not in r.headers, slug
    # they still exist and work with a normal password login
    r = client.post("/auth/login", json={"identifier": "demo.teacher@example.com", "password": PW},
                    headers={"X-Elevia-Web": "1"})
    assert r.status_code == 200, r.text


def test_teacher_demo_needs_the_judges_access_code(client, demo_on, monkeypatch):
    seed(activity=False)
    # off unless the server has a code configured
    assert demo_login(client, "teacher").status_code == 403
    assert client.get("/demo/accounts").json()["teacher"]["available"] is False
    monkeypatch.setenv("ELEVIA_DEMO_TEACHER_CODE", "judges-2026-code")
    d = client.get("/demo/accounts").json()
    assert d["teacher"]["available"] is True and "judges-2026-code" not in str(d)          # code never sent
    for wrong in ("", "judges", "JUDGES-2026-CODE"):
        r = client.post("/demo/login", json={"slug": "teacher", "access_code": wrong}, headers={"X-Elevia-Web": "1"})
        assert r.status_code == 403 and "set-cookie" not in r.headers
    r = client.post("/demo/login", json={"slug": "teacher", "access_code": "judges-2026-code"},
                    headers={"X-Elevia-Web": "1"})
    assert r.status_code == 200 and "token" not in r.json()
    tok = r.cookies.get("elevia_session") or r.headers["set-cookie"].split("elevia_session=")[1].split(";")[0]
    assert client.get("/auth/me", headers=H(tok)).json()["user"]["role"] == "teacher"
    # a code shorter than 8 characters is treated as "off"
    monkeypatch.setenv("ELEVIA_DEMO_TEACHER_CODE", "short")
    assert client.post("/demo/login", json={"slug": "teacher", "access_code": "short"},
                       headers={"X-Elevia-Web": "1"}).status_code == 403


def test_wrong_teacher_codes_are_rate_limited(client, demo_on, monkeypatch):
    monkeypatch.setenv("ELEVIA_DEMO_TEACHER_CODE", "judges-2026-code")
    seed(activity=False)
    codes = [client.post("/demo/login", json={"slug": "teacher", "access_code": f"guess-{i}"},
                         headers={"X-Elevia-Web": "1"}).status_code for i in range(11)]
    assert codes[:10] == [403] * 10 and codes[10] == 429
    # even the right code waits until the window passes
    assert client.post("/demo/login", json={"slug": "teacher", "access_code": "judges-2026-code"},
                       headers={"X-Elevia-Web": "1"}).status_code == 429


def test_demo_login_never_reaches_real_accounts(client, demo_on):
    token, uid = make_learner(client, email="demo.learner@example.com")   # a real person took a demo email
    with pytest.raises(SystemExit):
        seed()
    assert count("SELECT COUNT(*) FROM demo_registry") == 0                # stopped before changing anything
    assert count("SELECT COUNT(*) FROM users") == 1
    assert demo_login(client, "fresh").status_code == 409


def test_demo_login_is_rate_limited(client, demo_on):
    seed(activity=False)
    codes = [demo_login(client, "fresh").status_code for _ in range(61)]
    assert codes[:60] == [200] * 60 and codes[60] == 429


def test_shared_demo_accounts_cannot_break_the_demo(client, demo_on):
    seed(activity=False)
    tok = staff_login(client, "parent").cookies.get("elevia_session")
    kid = db_one("SELECT ref_id FROM demo_registry WHERE slug='riya'")[0]
    r = client.post(f"/parent/children/{kid}/withdraw-consent", headers=H(tok))
    assert r.status_code == 403 and "shared demo account" in r.json()["detail"]
    r = client.put(f"/parent/children/{kid}/permissions", json={"permissions": []}, headers=H(tok))
    assert r.status_code == 403
    ftok = demo_login(client, "fresh").cookies.get("elevia_session")
    assert client.post("/sharing/invite", json={"email": "x@example.org", "scopes": ["progress"]},
                       headers=H(ftok)).status_code == 403
    assert db_one("SELECT status FROM users WHERE id=?", kid)[0] == "active"


def test_reset_restores_demo_and_never_touches_real_users(client, demo_on):
    real_tok, real_id = make_learner(client, email="real.person@example.org")
    client.post("/learn/start", json={"grade": 9, "topic_id": "loops"}, headers=H(real_tok))
    real_cases = count("SELECT COUNT(*) FROM cases")
    seed()
    seeded = {t: count(f"SELECT COUNT(*) FROM {t}") for t in ("users", "cases", "responses", "gaps", "schools")}
    # a judge changes things
    ttok = staff_login(client, "teacher").cookies.get("elevia_session")
    case = db_one("SELECT id FROM cases WHERE stage='teacher_review'")[0]
    client.post(f"/progress/cases/{case}/decision", json={"decision": "reject", "reason": "judge tried it"}, headers=H(ttok))
    fr = demo_login(client, "fresh").cookies.get("elevia_session")
    client.post("/learn/start", json={"grade": 7, "topic_id": "decimals"}, headers=H(fr))
    out = demo_script.reset(password=PW)
    assert out["deleted"]["users"] == 13
    after = {t: count(f"SELECT COUNT(*) FROM {t}") for t in seeded}
    assert after == seeded                                                    # back to the same known state
    assert count("SELECT COUNT(*) FROM cases WHERE stage='teacher_review'") == 3
    # the real user and their learning are untouched
    assert db_one("SELECT email FROM users WHERE id=?", real_id)[0] == "real.person@example.org"
    me = client.get("/learn/state", params={"topic": "loops"}, headers=H(real_tok)).json()
    assert me["phase"] == "checkin" and real_cases == 1
    assert count("SELECT COUNT(*) FROM demo_registry WHERE kind='user'") == 13


def test_demo_story_is_realistic_and_consistent_across_dashboards(client, demo_on):
    seed()
    tok = {s: (staff_login if s in STAFF_LOGIN else demo_login)(client, s).cookies.get("elevia_session")
           for s in ("riya", "arjun", "teacher", "parent")}
    riya = client.get("/learn/dashboard", headers=H(tok["riya"])).json()
    arjun = client.get("/learn/dashboard", headers=H(tok["arjun"])).json()
    assert riya["student"]["grade"] == 9
    assert riya["totals"]["skills_mastered"] == 8 and riya["upcoming_retests"] and riya["open_gaps"]
    outcomes = {h["outcome"] for h in riya["history"]}
    assert {"Gap closed", "No gap found"} <= outcomes
    assert any(c["phase"] == "teacher_wait" for c in arjun["continue_learning"])
    # Riya's linear equations: a failed retest, a new plan, then a pass
    rid = db_one("SELECT ref_id FROM demo_registry WHERE slug='riya'")[0]
    det = client.get(f"/progress/students/{rid}", headers=H(tok["teacher"])).json()
    lin = next(t for t in det["topics"] if t["topic_id"] == "linear_equations")
    assert [r["passed"] for r in lin["rounds"][0]["gap"]["retests"]] == [False, True]
    # teacher sees the same numbers the students see
    grp = client.get("/progress/students", headers=H(tok["teacher"])).json()["groups"][0]
    rows = {s["name"]: s for s in grp["students"]}
    assert len(rows) == 5
    assert rows["Riya Sharma"]["answers"] == riya["answers"]["total"]
    assert rows["Arjun Patel"]["answers"] == arjun["answers"]["total"]
    assert rows["Riya Sharma"]["skills_mastered"] == riya["totals"]["skills_mastered"]
    assert rows["Arjun Patel"]["needs_review"] == 2 and rows["Riya Sharma"]["needs_review"] == 1
    # parent sees only Riya
    pg = client.get("/progress/students", headers=H(tok["parent"])).json()["groups"]
    assert [s["name"] for g in pg for s in g["students"]] == ["Riya Sharma"]
    aid = db_one("SELECT ref_id FROM demo_registry WHERE slug='arjun'")[0]
    assert client.get(f"/progress/students/{aid}", headers=H(tok["parent"])).status_code == 404
    # history spreads over six months
    assert count("SELECT COUNT(DISTINCT substr(created_at,1,7)) FROM cases") >= 6


def test_next_step_queue_and_intervention_history(client, demo_on):
    seed()
    tok = {s: (staff_login if s in STAFF_LOGIN else demo_login)(client, s).cookies.get("elevia_session")
           for s in ("riya", "arjun", "fresh", "teacher")}
    riya = client.get("/learn/dashboard", headers=H(tok["riya"])).json()["next_step"]
    assert riya["kind"] == "learn" and riya["topic_id"] == "data_types"          # lesson in progress first
    arjun = client.get("/learn/dashboard", headers=H(tok["arjun"])).json()["next_step"]
    assert arjun["kind"] == "verify" and arjun["topic_id"] == "linear_equations"  # unfinished double-check
    fresh = client.get("/learn/dashboard", headers=H(tok["fresh"])).json()
    assert fresh["needs_grade"] is True and fresh["next_step"]["kind"] == "start"
    t = client.get("/progress/students", headers=H(tok["teacher"])).json()
    assert {(q["student"], q["topic"]) for q in t["queue"]} == {
        ("Arjun Patel", "Fractions"), ("Arjun Patel", "Integers"), ("Riya Sharma", "Past tense verbs")}
    assert t["interventions"][0]["action"] == "change_focus"                       # newest first
    assert {i["action"] for i in t["interventions"]} == {"confirm_gap", "reject_gap", "note", "change_focus"}
    # once the retest unlocks, it becomes the next step
    with __import__("backend.db", fromlist=["x"]).transaction() as c:
        c.execute("UPDATE assessments SET available_at='2000-01-01T00:00:00+00:00' WHERE kind='retest' AND status='open'")
    riya = client.get("/learn/dashboard", headers=H(tok["riya"])).json()["next_step"]
    assert riya["kind"] == "retest" and riya["topic_id"] == "ratio_proportion"
    # parents get no queue
    ptok = staff_login(client, "parent").cookies.get("elevia_session")
    assert client.get("/progress/students", headers=H(ptok)).json()["queue"] == []
