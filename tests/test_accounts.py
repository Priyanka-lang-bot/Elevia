"""Accounts, consent, schools, sharing and access restrictions, through the HTTP routes."""
import re
import sqlite3
from datetime import date, timedelta

import pytest

from backend import db
from backend.accounts import schools

PW = "Correct-horse-42"


def dob(years: int) -> str:
    t = date.today()
    return t.replace(year=t.year - years).isoformat() if not (t.month == 2 and t.day == 29) else \
        (t - timedelta(days=365 * years + years // 4)).isoformat()


def H(token):
    return {"Authorization": f"Bearer {token}"}


def last_link_token(to_email: str) -> str:
    with db.transaction() as c:
        row = c.execute("SELECT body FROM email_outbox WHERE to_email=? ORDER BY id DESC LIMIT 1", (to_email,)).fetchone()
    assert row, f"no email to {to_email}"
    return re.search(r"token=([A-Za-z0-9_\-]+)", row["body"]).group(1)


def db_one(sql, *args):
    with db.transaction() as c:
        return c.execute(sql, args).fetchone()


# ---------------------------------------------------------------- helpers to build accounts

def make_learner(client, email="ada@example.com", verify=True):
    r = client.post("/auth/register/learner", json={"full_name": "Ada Learner", "date_of_birth": dob(25),
                                                     "email": email, "password": PW, "accept_terms": True})
    assert r.status_code == 201, r.text
    if verify:
        assert client.post("/auth/verify-email", json={"token": last_link_token(email)}).status_code == 200
    return r.json()["token"], r.json()["user"]["id"]


def make_child(client, username="riya_s", parent_email="mum@example.com"):
    r = client.post("/auth/register/student", json={
        "full_name": "Riya Sharma", "date_of_birth": dob(12), "username": username, "password": PW,
        "parent_name": "Meena Sharma", "parent_email": parent_email})
    assert r.status_code == 201, r.text
    return r.json()["token"], r.json()["user"]["id"]


def consent(client, parent_email="mum@example.com", perms=("view_progress", "view_assessments"), **extra):
    body = {"token": last_link_token(parent_email), "is_parent_or_guardian": True, "is_adult": True,
            "agree_purposes": True, "permissions": list(perms), "full_name": "Meena Sharma", "password": PW}
    body.update(extra)
    return client.post("/consent/accept", json=body)


def setup_school(client, name="Sunrise Public School", admin_email="head@sunrise.in"):
    with db.transaction() as c:
        out = schools.create_school(c, name=name, admin_email=admin_email, state="Maharashtra", district="Pune")
    tok = re.search(r"token=([A-Za-z0-9_\-]+)", out["invite_url"]).group(1)
    r = client.post("/invites/accept", json={"token": tok, "full_name": "Head Admin", "password": PW})
    assert r.status_code == 201, r.text
    admin = r.json()["token"]
    cls = client.post("/school/classes", json={"grade": 7, "division": "b", "academic_year": "2026-27"},
                      headers=H(admin)).json()
    return out["school_id"], admin, cls["id"]


def add_teacher(client, admin, class_id, email, can_codes=False):
    assert client.post("/school/teachers/invite", json={"email": email}, headers=H(admin)).status_code == 200
    r = client.post("/invites/accept", json={"token": last_link_token(email), "full_name": "T " + email[:3],
                                             "password": PW})
    t_token, t_id = r.json()["token"], r.json()["user"]["id"]
    if class_id:
        assert client.post("/school/assignments", json={"teacher_id": t_id, "class_id": class_id,
                                                        "can_create_codes": can_codes},
                           headers=H(admin)).status_code == 200
    return t_token, t_id


# ---------------------------------------------------------------- passwords and login

def test_password_is_hashed_never_plaintext(client):
    make_learner(client)
    row = db_one("SELECT password_hash FROM users WHERE email='ada@example.com'")
    assert row["password_hash"].startswith("scrypt$") and PW not in row["password_hash"]


@pytest.mark.parametrize("pw,msg", [("short", "at least 8"), ("password123", "too common"), ("x" * 129, "at most")])
def test_weak_passwords_rejected(client, pw, msg):
    r = client.post("/auth/register/learner", json={"full_name": "Ada L", "date_of_birth": dob(30),
                                                     "email": "a@example.com", "password": pw, "accept_terms": True})
    assert r.status_code in (400, 422) and (r.status_code == 422 or msg in r.json()["detail"])


def test_signup_validation_and_duplicates(client):
    bad = client.post("/auth/register/learner", json={"full_name": "Ada", "date_of_birth": dob(30),
                                                       "email": "not-an-email", "password": PW, "accept_terms": True})
    assert bad.status_code == 400 and bad.json()["field"] == "email"
    no_terms = client.post("/auth/register/learner", json={"full_name": "Ada L", "date_of_birth": dob(30),
                                                            "email": "b@example.com", "password": PW})
    assert no_terms.json()["field"] == "accept_terms"
    make_learner(client)
    dup = client.post("/auth/register/learner", json={"full_name": "Ada Two", "date_of_birth": dob(30),
                                                       "email": "ADA@example.com", "password": PW, "accept_terms": True})
    assert dup.status_code == 409 and dup.json()["code"] == "email_taken"
    make_child(client)
    dup_user = client.post("/auth/register/student", json={"full_name": "Other Kid", "date_of_birth": dob(10),
                                                            "username": "Riya_S", "password": PW,
                                                            "parent_name": "Pa Rent", "parent_email": "p2@example.com"})
    assert dup_user.status_code == 409 and dup_user.json()["code"] == "username_taken"


def test_age_routes_to_correct_pathway(client):
    young = client.post("/auth/register/learner", json={"full_name": "Kid K", "date_of_birth": dob(15),
                                                         "email": "k@example.com", "password": PW, "accept_terms": True})
    assert young.json()["code"] == "use_student"
    adult = client.post("/auth/register/student", json={"full_name": "Grown Up", "date_of_birth": dob(19),
                                                         "username": "grownup", "password": PW,
                                                         "parent_name": "Pa Rent", "parent_email": "p@example.com"})
    assert adult.json()["code"] == "use_learner"
    future = client.post("/auth/register/learner", json={"full_name": "Time T", "date_of_birth": "2999-01-01",
                                                          "email": "t@example.com", "password": PW, "accept_terms": True})
    assert future.json()["field"] == "date_of_birth"


def test_login_errors_are_generic_and_lock_out(client):
    make_learner(client)
    wrong = client.post("/auth/login", json={"identifier": "ada@example.com", "password": "wrong-pass-1"})
    ghost = client.post("/auth/login", json={"identifier": "ghost@example.com", "password": "wrong-pass-1"})
    assert wrong.status_code == ghost.status_code == 401 and wrong.json()["detail"] == ghost.json()["detail"]
    for _ in range(4):
        client.post("/auth/login", json={"identifier": "ada@example.com", "password": "wrong-pass-1"})
    locked = client.post("/auth/login", json={"identifier": "ada@example.com", "password": PW})
    assert locked.status_code == 429
    for _ in range(5):
        client.post("/auth/login", json={"identifier": "ghost@example.com", "password": "x" * 9})
    assert client.post("/auth/login", json={"identifier": "ghost@example.com", "password": "x" * 9}).status_code == 429


def test_sessions_and_logout(client):
    token, _ = make_learner(client)
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers=H("made-up-token")).status_code == 401
    assert client.get("/auth/me", headers=H(token)).json()["next_step"] == "onboarding"
    client.post("/auth/logout", headers=H(token))
    assert client.get("/auth/me", headers=H(token)).status_code == 401
    assert db_one("SELECT COUNT(*) n FROM auth_sessions WHERE token_hash=?", token)["n"] == 0  # only hashes stored


def test_email_verification_gates_account(client):
    token, _ = make_learner(client, verify=False)
    assert client.get("/auth/me", headers=H(token)).json()["next_step"] == "verify_email"
    assert client.get("/sharing", headers=H(token)).status_code == 403
    tok = last_link_token("ada@example.com")
    assert client.post("/auth/verify-email", json={"token": tok}).json()["status"] == "active"
    assert client.post("/auth/verify-email", json={"token": tok}).status_code == 400  # single use
    assert client.get("/sharing", headers=H(token)).status_code == 200


def test_forgot_and_reset_password(client):
    token, _ = make_learner(client)
    unknown = client.post("/auth/forgot-password", json={"email": "nobody@example.com"})
    known = client.post("/auth/forgot-password", json={"email": "ada@example.com"})
    assert unknown.json() == known.json()  # can't tell which emails exist
    reset = last_link_token("ada@example.com")
    assert client.post("/auth/reset-password", json={"token": reset, "new_password": "New-secret-77"}).status_code == 200
    assert client.get("/auth/me", headers=H(token)).status_code == 401  # old sessions revoked
    assert client.post("/auth/reset-password", json={"token": reset, "new_password": "Another-88x"}).status_code == 400
    assert client.post("/auth/login", json={"identifier": "ada@example.com", "password": "New-secret-77"}).status_code == 200


# ---------------------------------------------------------------- pathway 1: individual student + parent

def test_individual_student_locked_until_parent_consents(client):
    s_token, s_id = make_child(client)
    me = client.get("/auth/me", headers=H(s_token)).json()
    assert me["next_step"] == "await_parent_consent" and me["consent_request"]["sent_to"].startswith("mu")
    assert client.get(f"/people/{s_id}/summary", headers=H(s_token)).status_code == 403

    info = client.post("/consent/info", json={"token": last_link_token("mum@example.com")}).json()
    assert info["child_first_name"] == "Riya" and not info["parent_has_account"]

    no_decl = consent(client, is_adult=False)
    assert no_decl.status_code == 400 and no_decl.json()["field"] == "declarations"

    r = consent(client)
    assert r.status_code == 200, r.text
    p_token = r.json()["token"]
    assert client.get("/auth/me", headers=H(s_token)).json()["next_step"] == "onboarding"
    rec = db_one("SELECT * FROM consent_records WHERE student_user_id=?", s_id)
    assert rec["action"] == "granted" and rec["created_at"] and rec["method"] == "email_link+declaration"
    parent = db_one("SELECT * FROM users WHERE email='mum@example.com'")
    assert parent["role"] == "parent" and parent["email_verified_at"]

    summary = client.get(f"/people/{s_id}/summary", headers=H(p_token)).json()
    assert summary["access_via"] == "parent_link"
    assert "assessments" in summary["visible_scopes"] and "activity" not in summary["visible_scopes"]
    assert consent(client).status_code == 400  # link can't be reused


def test_entering_parent_email_grants_nothing_before_consent(client):
    # someone already has a parent account with that email
    _, first_child = make_child(client, "first_kid", "dad@example.com")
    dad = consent(client, "dad@example.com", full_name="Dad Kumar").json()["token"]
    _, second = make_child(client, "second_kid", "dad@example.com")
    assert client.get(f"/people/{second}/summary", headers=H(dad)).status_code == 404
    # existing parent must authenticate before consenting
    no_login = consent(client, "dad@example.com", password=None)
    assert no_login.status_code == 401 and no_login.json()["code"] == "login_required"
    ok = client.post("/consent/accept", headers=H(dad), json={
        "token": last_link_token("dad@example.com"), "is_parent_or_guardian": True, "is_adult": True,
        "agree_purposes": True, "permissions": ["view_progress"]})
    assert ok.status_code == 200
    kids = client.get("/parent/children", headers=H(dad)).json()
    assert {k["student_id"] for k in kids} == {first_child, second}


def test_parent_permissions_and_withdrawal(client):
    s_token, s_id = make_child(client)
    p_token = consent(client).json()["token"]
    assert client.put(f"/parent/children/{s_id}/permissions", json={"permissions": ["view_activity"]},
                      headers=H(p_token)).status_code == 200
    scopes = client.get(f"/people/{s_id}/summary", headers=H(p_token)).json()["visible_scopes"]
    assert "activity" in scopes and "progress" not in scopes
    assert client.post(f"/parent/children/{s_id}/withdraw-consent", headers=H(p_token)).status_code == 200
    assert client.get(f"/people/{s_id}/summary", headers=H(p_token)).status_code == 404
    assert client.get("/auth/me", headers=H(s_token)).status_code == 401  # student signed out
    assert client.post("/auth/login", json={"identifier": "riya_s", "password": PW}).status_code == 403
    actions = [r["action"] for r in client.get("/parent/children", headers=H(p_token)).json()[0]["consent_history"]]
    assert actions == ["granted", "updated", "withdrawn"]


def test_other_parent_cannot_see_or_control_child(client):
    _, s_id = make_child(client, "kid_a", "a@example.com")
    consent(client, "a@example.com", full_name="Parent A")
    _, other = make_child(client, "kid_b", "b@example.com")
    b = consent(client, "b@example.com", full_name="Parent B").json()["token"]
    assert client.get(f"/people/{s_id}/summary", headers=H(b)).status_code == 404
    assert client.put(f"/parent/children/{s_id}/permissions", json={"permissions": []}, headers=H(b)).status_code == 404
    assert client.post(f"/parent/children/{s_id}/withdraw-consent", headers=H(b)).status_code == 404


def test_decline_deletes_request_and_parent_email_of_other_role(client):
    _, s_id = make_child(client)
    assert client.post("/consent/decline", json={"token": last_link_token("mum@example.com")}).status_code == 200
    assert db_one("SELECT COUNT(*) n FROM users WHERE id=?", s_id)["n"] == 0
    make_learner(client, "adult@example.com")
    make_child(client, "kid_c", "adult@example.com")
    r = consent(client, "adult@example.com", password=PW)
    assert r.status_code == 409 and r.json()["code"] == "email_other_role"


def test_unconsented_accounts_purged_after_14_days(client):
    _, s_id = make_child(client)
    old = (date.today() - timedelta(days=15)).isoformat() + "T00:00:00+00:00"
    with db.transaction() as c:
        c.execute("UPDATE users SET created_at=? WHERE id=?", (old, s_id))
    make_child(client, "new_kid", "x@example.com")  # sign-up triggers the purge
    assert db_one("SELECT COUNT(*) n FROM users WHERE id=?", s_id)["n"] == 0


# ---------------------------------------------------------------- pathway 2: school

def school_student(client, code, username="aarav7", parent_email="papa@example.com", client_id="dev-1"):
    return client.post("/auth/register/school-student", headers={"X-Client-Id": client_id}, json={
        "code": code, "full_name": "Aarav Patel", "date_of_birth": dob(12), "username": username,
        "password": PW, "parent_name": "Raj Patel", "parent_email": parent_email})


def test_school_flow_codes_consent_teacher_approval(client):
    school_id, admin, class_id = setup_school(client)
    t_token, _ = add_teacher(client, admin, class_id, "asha@sunrise.in")
    other_class = client.post("/school/classes", json={"grade": 8, "division": "A", "academic_year": "2026-27"},
                              headers=H(admin)).json()["id"]
    other_t, _ = add_teacher(client, admin, other_class, "ben@sunrise.in")

    code = client.post("/school/codes", json={"class_id": class_id}, headers=H(admin)).json()["code"]
    assert re.fullmatch(r"ELV-[2-9A-HJKMNP-Z]{4}-[2-9A-HJKMNP-Z]{4}", code)
    v = client.post("/auth/school-code/validate", json={"code": code.lower().replace("-", " ")}).json()
    assert v == {"school_name": "Sunrise Public School", "class_label": "Class 7 B, 2026-27"}

    r = school_student(client, code)
    assert r.status_code == 201, r.text
    s_token, s_id = r.json()["token"], r.json()["user"]["id"]
    assert client.get("/auth/me", headers=H(s_token)).json()["next_step"] == "await_parent_consent"
    # nobody at school sees a student whose consent is pending
    assert client.get(f"/people/{s_id}/summary", headers=H(admin)).status_code == 404

    consent(client, "papa@example.com", full_name="Raj Patel")
    assert client.get("/auth/me", headers=H(s_token)).json()["next_step"] == "await_teacher_approval"
    assert client.get(f"/people/{s_id}/summary", headers=H(t_token)).status_code == 404  # not approved yet

    roster = client.get(f"/school/classes/{class_id}/roster", headers=H(t_token)).json()
    enr = roster["students"][0]
    assert enr["status"] == "pending"
    assert client.get(f"/school/classes/{class_id}/roster", headers=H(other_t)).status_code == 404
    assert client.post(f"/school/enrollments/{enr['enrollment_id']}/approve", headers=H(other_t)).status_code == 404
    assert client.post(f"/school/enrollments/{enr['enrollment_id']}/approve", headers=H(admin)).status_code == 403
    assert client.post(f"/school/enrollments/{enr['enrollment_id']}/approve", headers=H(t_token)).status_code == 200

    me = client.get("/auth/me", headers=H(s_token)).json()
    assert me["next_step"] == "onboarding" and me["student"]["class"]["school_name"] == "Sunrise Public School"
    t_view = client.get(f"/people/{s_id}/summary", headers=H(t_token)).json()
    assert t_view["access_via"] == "teacher_class" and "progress" in t_view["visible_scopes"]
    assert client.get(f"/people/{s_id}/summary", headers=H(other_t)).status_code == 404  # same school, other class
    a_view = client.get(f"/people/{s_id}/summary", headers=H(admin)).json()
    assert a_view["visible_scopes"] == ["profile", "roster"]  # admin: roster only, no learning data


def test_referral_code_rules(client):
    _, admin, class_id = setup_school(client)
    bad = client.post("/auth/school-code/validate", headers={"X-Client-Id": "c1"}, json={"code": "ELV-AAAA-BBBB"})
    assert bad.status_code == 400 and bad.json()["code"] == "bad_code"
    for _ in range(4):
        client.post("/auth/school-code/validate", headers={"X-Client-Id": "c1"}, json={"code": "ELV-AAAA-BBBB"})
    assert client.post("/auth/school-code/validate", headers={"X-Client-Id": "c1"},
                       json={"code": "ELV-AAAA-BBBB"}).status_code == 429

    one_use = client.post("/school/codes", json={"class_id": class_id, "max_uses": 1}, headers=H(admin)).json()["code"]
    assert school_student(client, one_use, "kid1", "p1@example.com", "c2").status_code == 201
    assert school_student(client, one_use, "kid2", "p2@example.com", "c3").json()["code"] == "bad_code"

    rev = client.post("/school/codes", json={"class_id": class_id}, headers=H(admin)).json()
    code_id = [c for c in client.get("/school/codes", headers=H(admin)).json() if c["code"] == rev["code"]][0]["id"]
    client.post(f"/school/codes/{code_id}/revoke", headers=H(admin))
    assert client.post("/auth/school-code/validate", headers={"X-Client-Id": "c4"},
                       json={"code": rev["code"]}).status_code == 400

    exp = client.post("/school/codes", json={"class_id": class_id}, headers=H(admin)).json()["code"]
    with db.transaction() as c:
        c.execute("UPDATE referral_codes SET expires_at='2000-01-01T00:00:00+00:00' WHERE code=?", (exp,))
    assert client.post("/auth/school-code/validate", headers={"X-Client-Id": "c5"}, json={"code": exp}).status_code == 400

    live = client.post("/school/codes", json={"class_id": class_id}, headers=H(admin)).json()["code"]
    with db.transaction() as c:
        c.execute("UPDATE schools SET subscription_status='lapsed'")
    assert client.post("/auth/school-code/validate", headers={"X-Client-Id": "c6"}, json={"code": live}).status_code == 400
    assert client.post("/school/codes", json={"class_id": class_id}, headers=H(admin)).status_code == 403


def test_teacher_code_permission_and_school_isolation(client):
    _, admin, class_id = setup_school(client)
    t_token, t_id = add_teacher(client, admin, class_id, "asha@sunrise.in")
    assert client.post("/school/codes", json={"class_id": class_id}, headers=H(t_token)).status_code == 403
    client.post("/school/assignments", json={"teacher_id": t_id, "class_id": class_id, "can_create_codes": True},
                headers=H(admin))
    code = client.post("/school/codes", json={"class_id": class_id}, headers=H(t_token)).json()["code"]
    assert client.post("/school/classes", json={"grade": 9, "division": "A", "academic_year": "2026-27"},
                       headers=H(t_token)).status_code == 403  # admin-only

    r = school_student(client, code, "kid_s1", "pp@example.com")
    s_id = r.json()["user"]["id"]
    consent(client, "pp@example.com", full_name="Pa Parent")
    _, admin2, class2 = setup_school(client, "Other School", "head@other.in")
    assert client.get(f"/people/{s_id}/summary", headers=H(admin2)).status_code == 404
    assert client.get(f"/school/classes/{class_id}/roster", headers=H(admin2)).status_code == 404


def test_school_handled_consent_skips_parent(client):
    _, admin, class_id = setup_school(client)
    with db.transaction() as c:
        c.execute("UPDATE schools SET consent_handled_by_school=1")
    code = client.post("/school/codes", json={"class_id": class_id}, headers=H(admin)).json()["code"]
    r = client.post("/auth/register/school-student", json={"code": code, "full_name": "Zoya Khan",
                                                           "date_of_birth": dob(13), "username": "zoya13",
                                                           "password": PW})
    assert r.status_code == 201 and r.json()["user"]["status"] == "active"
    assert client.get("/auth/me", headers=H(r.json()["token"])).json()["next_step"] == "await_teacher_approval"


# ---------------------------------------------------------------- pathway 3: adult sharing

def test_adult_learner_shares_only_what_they_choose(client):
    l_token, l_id = make_learner(client)
    _, kid = make_child(client, "kid_z", "mentor@example.com")
    mentor = consent(client, "mentor@example.com", full_name="Mentor Mehta").json()["token"]
    assert client.get(f"/people/{l_id}/summary", headers=H(mentor)).status_code == 404  # nothing by default

    inv = client.post("/sharing/invite", json={"email": "mentor@example.com", "scopes": ["progress"]},
                      headers=H(l_token))
    assert inv.status_code == 201
    grant_id = inv.json()["grant_id"]
    assert client.get(f"/people/{l_id}/summary", headers=H(mentor)).status_code == 404  # not accepted yet

    stranger, _ = make_learner(client, "stranger@example.com")
    share_tok = last_link_token("mentor@example.com")
    assert client.post("/sharing/accept", json={"token": share_tok}, headers=H(stranger)).status_code == 403
    assert client.post("/sharing/accept", json={"token": share_tok}, headers=H(mentor)).status_code == 200

    view = client.get(f"/people/{l_id}/summary", headers=H(mentor)).json()
    assert view["access_via"] == "share_grant" and view["visible_scopes"] == ["profile", "progress"]
    client.put(f"/sharing/{grant_id}/scopes", json={"scopes": ["progress", "gaps"]}, headers=H(l_token))
    assert "gaps" in client.get(f"/people/{l_id}/summary", headers=H(mentor)).json()["visible_scopes"]

    mine = client.get("/sharing", headers=H(l_token)).json()
    assert mine["access_log"] and mine["access_log"][0]["viewer"] == "Mentor Mehta"
    client.post(f"/sharing/{grant_id}/revoke", headers=H(l_token))
    assert client.get(f"/people/{l_id}/summary", headers=H(mentor)).status_code == 404
    # a stranger can't change someone else's grant
    assert client.post(f"/sharing/{grant_id}/revoke", headers=H(stranger)).status_code == 404


def test_access_requests_approve_and_reject(client):
    l_token, l_id = make_learner(client)
    _, admin, class_id = setup_school(client)
    t_token, _ = add_teacher(client, admin, class_id, "asha@sunrise.in")
    a = client.post("/sharing/request", json={"learner_email": "ada@example.com"}, headers=H(t_token)).json()
    b = client.post("/sharing/request", json={"learner_email": "nobody@example.com"}, headers=H(t_token)).json()
    assert a == b  # doesn't reveal who has an account
    req = client.get("/sharing", headers=H(l_token)).json()["requests"][0]
    assert client.get(f"/people/{l_id}/summary", headers=H(t_token)).status_code == 404
    client.post(f"/sharing/{req['id']}/respond", json={"approve": True, "scopes": ["assessments"]}, headers=H(l_token))
    assert client.get(f"/people/{l_id}/summary", headers=H(t_token)).json()["visible_scopes"] == ["profile", "assessments"]
    with_me = client.get("/sharing/with-me", headers=H(t_token)).json()
    assert with_me[0]["owner_name"] == "Ada Learner"

    second, _ = add_teacher(client, admin, class_id, "ben@sunrise.in")
    client.post("/sharing/request", json={"learner_email": "ada@example.com"}, headers=H(second))
    req2 = client.get("/sharing", headers=H(l_token)).json()["requests"][0]
    client.post(f"/sharing/{req2['id']}/respond", json={"approve": False}, headers=H(l_token))
    assert client.get(f"/people/{l_id}/summary", headers=H(second)).status_code == 404


def test_students_cannot_manage_or_request_sharing(client):
    s_token, _ = make_child(client)
    consent(client)
    assert client.post("/sharing/invite", json={"email": "x@example.com", "scopes": ["progress"]},
                       headers=H(s_token)).status_code == 403
    assert client.post("/sharing/request", json={"learner_email": "x@example.com"},
                       headers=H(s_token)).status_code == 403


def test_dev_outbox_hidden_unless_enabled(client, monkeypatch):
    assert client.get("/dev/outbox").status_code == 404
    monkeypatch.setenv("ELEVIA_DEV_OUTBOX", "1")
    make_learner(client, verify=False)
    assert "Confirm your email" in client.get("/dev/outbox").json()[0]["subject"]
