"""Demo environment for judges: create, reset or inspect the fictional demo accounts.

    python scripts/demo.py seed      create demo accounts + realistic activity (refuses if they exist)
    python scripts/demo.py reset     delete ONLY demo data (rows listed in demo_registry), then seed again
    python scripts/demo.py status    show which demo accounts exist

Uses the database configured in .env (local SQLite, or Turso when TURSO_DATABASE_URL is set).

Everything is created through the REAL routes (sign-up, parent consent, invitations, teacher approval)
and the learning history is produced by answering questions through the REAL workflow (Diagnoser,
Checker, Planner, Tutor, retests). Nothing is written directly except: timestamps of demo cases are moved
into the past so the history looks like two weeks of use, and the retest delay is skipped while seeding.

Safety: reset deletes only users and schools recorded in `demo_registry` when this script created them,
and the learning records linked to those users. If a demo username/email is already used by an account
that is NOT in the registry (e.g. a real user), seeding stops and nothing is deleted.
The password below is for convenience on local machines; on a shared server use ELEVIA_DEMO_MODE=1 and the
one-click demo login instead, so judges never need it.
"""
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from backend import db  # noqa: E402
from backend.accounts import schools  # noqa: E402
from backend.content import misconceptions, questions  # noqa: E402
from backend.db import now_iso  # noqa: E402
from backend.engine import correct_answer_text  # noqa: E402
from backend.main import app  # noqa: E402

PW = "Demo-Pass-2026!"
ADMIN, TEACHER, LEARNER = "demo.admin@example.com", "demo.teacher@example.com", "demo.learner@example.com"
PARENT_RIYA, PARENT_ARJUN = "demo.parent@example.com", "demo.parent2@example.com"
RIYA, ARJUN = "riya.demo", "arjun.demo"
DEMO_EMAILS = [ADMIN, TEACHER, LEARNER, PARENT_RIYA, PARENT_ARJUN]
DEMO_USERNAMES = [RIYA, ARJUN]
SCHOOL_NAME = "Sunrise Demo School"


# ---------------------------------------------------------------- helpers

def H(tok):
    return {"Authorization": f"Bearer {tok}"}


def ok(r, what):
    if r.status_code >= 300:
        raise SystemExit(f"FAILED at {what}: {r.status_code} {r.text}")
    return r.json()


def years_ago(n):
    t = datetime.now(timezone.utc).date()
    return t.replace(year=t.year - n, day=min(t.day, 28)).isoformat()


def token_from_outbox(to_email):
    with db.transaction() as c:
        row = c.execute("SELECT body FROM email_outbox WHERE to_email=? ORDER BY id DESC LIMIT 1", (to_email,)).fetchone()
    return re.search(r"token=([A-Za-z0-9_\-]+)", row["body"]).group(1)


def _pattern(q, gap_skill):
    mis = misconceptions()
    for ans, code in q.get("patterns", {}).items():
        if mis[code]["gap_skill"] == gap_skill:
            return ans
    return None


def _plain_wrong(q):
    if q["type"] == "mcq":
        bad = [o for o in q["options"] if o != q["answer"] and o not in q.get("patterns", {})]
        return bad[0] if bad else next(o for o in q["options"] if o != q["answer"])
    if q["type"] in ("numeric", "text", "code_output"):
        return "999"
    return "1/100"


class Student:
    """Drives one student's learning through the real /learn routes."""

    def __init__(self, c, ident):
        self.c = c
        self.h = H(ok(c.post("/auth/login", json={"identifier": ident, "password": PW}), f"login {ident}")["token"])

    def post(self, path, body):
        return ok(self.c.post(path, json=body, headers=self.h), path)

    def answer(self, st, choose, limit=None):
        n = 0
        for item in st["assessment"]["questions"]:
            if item["answered"]:
                continue
            if limit is not None and n >= limit:
                break
            q = questions()[item["id"]]
            out = self.post("/learn/answer", {"assessment_id": st["assessment"]["id"], "question_id": q["id"],
                                              "answer": choose(q)})
            st, n = out["state"], n + 1
        return st

    def start(self, topic):
        return self.post("/learn/start", {"topic_id": topic})

    def mistake_on(self, topic, skill):
        st = self.answer(self.start(topic), lambda q: _pattern(q, skill) or correct_answer_text(q))
        return st

    def confirm(self, st):
        with db.transaction() as conn:
            gs = conn.execute("SELECT skill_id FROM gaps WHERE case_id=? ORDER BY id DESC", (st["case_id"],)).fetchone()[0]
        return self.answer(st, lambda q: _pattern(q, gs) or _plain_wrong(q))

    def practise(self, st, limit=None):
        st = self.answer(st, correct_answer_text, limit)
        if limit is None and st["phase"] == "learn":
            st = self.post("/learn/practice/finish", {"assessment_id": st["assessment"]["id"]})
        return st

    def retest(self, st, topic, passed=True):
        with db.transaction() as conn:   # seeding only: skip the waiting time
            conn.execute("UPDATE assessments SET available_at=? WHERE case_id=? AND kind='retest' AND status='open'",
                         ("2000-01-01T00:00:00+00:00", st["case_id"]))
        st = self.post("/learn/retest/start", {"early": False, "topic_id": topic})
        return self.answer(st, correct_answer_text if passed else _plain_wrong)


# ---------------------------------------------------------------- accounts

def _conflicts(conn):
    marks = ",".join("?" * len(DEMO_EMAILS))
    rows = conn.execute(f"SELECT id FROM users WHERE email IN ({marks}) OR username IN (?,?)",
                        (*DEMO_EMAILS, *DEMO_USERNAMES)).fetchall()
    reg = {r["ref_id"] for r in conn.execute("SELECT ref_id FROM demo_registry WHERE kind='user'").fetchall()}
    return [r["id"] for r in rows if r["id"] not in reg]


def create_accounts(c) -> dict:
    with db.transaction() as conn:
        out = schools.create_school(conn, name=SCHOOL_NAME, admin_email=ADMIN, state="Maharashtra",
                                    district="Pune", is_demo=True)
        conn.execute("INSERT INTO demo_registry (kind, ref_id, slug, created_at) VALUES ('school',?,?,?)",
                     (out["school_id"], "school", now_iso()))
    admin = ok(c.post("/invites/accept", json={"token": token_from_outbox(ADMIN), "full_name": "Kavita Menon",
                                               "password": PW}), "admin invite")
    cls = ok(c.post("/school/classes", json={"grade": 6, "division": "A", "academic_year": "2026-27"},
                    headers=H(admin["token"])), "class")
    ok(c.post("/school/teachers/invite", json={"email": TEACHER}, headers=H(admin["token"])), "teacher invite")
    t = ok(c.post("/invites/accept", json={"token": token_from_outbox(TEACHER), "full_name": "Meera Iyer",
                                           "password": PW}), "teacher accept")
    ok(c.post("/school/assignments", json={"teacher_id": t["user"]["id"], "class_id": cls["id"],
                                           "can_create_codes": True}, headers=H(admin["token"])), "assign")
    code = ok(c.post("/school/codes", json={"class_id": cls["id"], "expires_days": 90, "max_uses": 40},
                     headers=H(t["token"])), "code")["code"]
    ids = {"admin": admin["user"]["id"], "teacher": t["user"]["id"]}
    for slug, uname, name, pname, pmail, perms in (
            ("riya", RIYA, "Riya Sharma", "Sunita Sharma", PARENT_RIYA,
             ["view_progress", "view_assessments", "view_activity"]),
            ("arjun", ARJUN, "Arjun Patel", "Raj Patel", PARENT_ARJUN, ["view_progress"])):
        s = ok(c.post("/auth/register/school-student", json={
            "full_name": name, "date_of_birth": years_ago(11), "username": uname, "password": PW,
            "parent_name": pname, "parent_email": pmail, "code": code}), f"{slug} sign-up")
        p = ok(c.post("/consent/accept", json={"token": token_from_outbox(pmail), "is_parent_or_guardian": True,
                                               "is_adult": True, "agree_purposes": True, "permissions": perms,
                                               "full_name": pname, "password": PW}), f"{slug} consent")
        ids[slug], ids["parent" if slug == "riya" else "parent2"] = s["user"]["id"], p["user"]["id"]
    with db.transaction() as conn:
        pending = [r["id"] for r in conn.execute(
            "SELECT id FROM class_enrollments WHERE class_id=? AND status='pending'", (cls["id"],)).fetchall()]
    for eid in pending:
        ok(c.post(f"/school/enrollments/{eid}/approve", headers=H(t["token"])), "approve")
    ok(c.post("/auth/register/learner", json={"full_name": "Ananya Rao", "date_of_birth": years_ago(19),
                                              "email": LEARNER, "password": PW, "accept_terms": True}), "learner")
    ok(c.post("/auth/verify-email", json={"token": token_from_outbox(LEARNER)}), "verify learner")
    with db.transaction() as conn:
        ids["fresh"] = conn.execute("SELECT id FROM users WHERE email=?", (LEARNER,)).fetchone()[0]
        for slug, uid in ids.items():
            conn.execute("INSERT INTO demo_registry (kind, ref_id, slug, created_at) VALUES ('user',?,?,?)",
                         (uid, slug, now_iso()))
    return {"code": code, "teacher_token": t["token"]}


# ---------------------------------------------------------------- learning history

def _shift_case(conn, case_id, hours):
    """Move every timestamp of one demo case `hours` into the past (keeps their order and gaps)."""
    d = timedelta(hours=hours)

    def sh(v):
        return (datetime.fromisoformat(v) - d).isoformat() if v else v
    for table, key, cols in (("cases", "id", ("created_at", "updated_at")),
                             ("assessments", "case_id", ("created_at", "completed_at", "available_at")),
                             ("gaps", "case_id", ("created_at", "verified_at")),
                             ("plans", "case_id", ("created_at",)), ("lessons", "case_id", ("created_at",)),
                             ("agent_runs", "case_id", ("started_at", "finished_at")),
                             ("teacher_overrides", "case_id", ("created_at",))):
        for row in conn.execute(f"SELECT rowid AS rid, {', '.join(cols)} FROM {table} WHERE {key}=?", (case_id,)).fetchall():
            conn.execute(f"UPDATE {table} SET {', '.join(c + '=?' for c in cols)} WHERE rowid=?",
                         (*[sh(row[c]) for c in cols], row["rid"]))
    for row in conn.execute("SELECT r.rowid AS rid, r.created_at FROM responses r JOIN assessments a "
                            "ON a.id=r.assessment_id WHERE a.case_id=?", (case_id,)).fetchall():
        conn.execute("UPDATE responses SET created_at=? WHERE rowid=?", (sh(row["created_at"]), row["rid"]))


def create_activity(c, teacher_token) -> dict:
    ages = {}
    riya = Student(c, RIYA)
    # decimals: confirmed gap -> lesson -> retest passed (mastered)
    st = riya.retest(riya.practise(riya.confirm(riya.mistake_on("decimals", "decimal_place_value"))), "decimals")
    ages[st["case_id"]] = 13 * 24
    # percentages: confirmed -> lesson -> retest FAILED -> new plan -> retest passed
    st = riya.confirm(riya.mistake_on("percentages", "percent_of_quantity"))
    st = riya.retest(riya.practise(st), "percentages", passed=False)
    st = riya.retest(riya.practise(st), "percentages")
    ages[st["case_id"]] = 9 * 24
    # forces and motion: all correct, no gap
    st = riya.answer(riya.start("forces_motion"), correct_answer_text)
    ages[st["case_id"]] = 6 * 24
    # past tense: confirmed gap, lesson in progress (2 practice answers)
    st = riya.practise(riya.confirm(riya.mistake_on("past_tense", "irregular_past")), limit=2)
    ages[st["case_id"]] = 2 * 24
    # loops: lesson finished, retest booked (not yet unlocked)
    st = riya.practise(riya.confirm(riya.mistake_on("loops", "loop_counting")))
    ages[st["case_id"]] = 3

    arjun = Student(c, ARJUN)
    # variables: suspected, but the double-check showed it was a slip
    st = arjun.mistake_on("variables", "variable_assignment")
    st = arjun.answer(st, correct_answer_text)
    ages[st["case_id"]] = 11 * 24
    # integers: confirmed -> lesson -> retest FAILED -> back to learning with a new plan
    st = arjun.retest(arjun.practise(arjun.confirm(arjun.mistake_on("integers", "adding_integers"))), "integers",
                      passed=False)
    integers_case = st["case_id"]
    ages[integers_case] = 8 * 24
    ok(c.post(f"/progress/cases/{integers_case}/note", json={"note": "Went over the number line with Arjun in class."},
              headers=H(teacher_token)), "teacher note")
    # fractions: one slip-like mistake, then mixed double-check -> waiting for the teacher
    st = arjun.answer(arjun.start("fractions"), lambda q: {"DA3": "2/5"}.get(q["id"]) or correct_answer_text(q))
    st = arjun.answer(st, lambda q: {"CD-V1": "3/4"}.get(q["id"]) or correct_answer_text(q))
    ages[st["case_id"]] = 4 * 24
    review_phase = st["phase"]
    # subject-verb agreement: confirmed gap, lesson ready
    st = arjun.confirm(arjun.mistake_on("subject_verb_agreement", "sva_tricky"))
    ages[st["case_id"]] = 3 * 24
    # linear equations: suspected gap, double-check not answered yet
    st = arjun.mistake_on("linear_equations", "one_step_equations")
    ages[st["case_id"]] = 12

    with db.transaction() as conn:
        for cid, hours in ages.items():
            _shift_case(conn, cid, hours)
    return {"arjun_fractions": review_phase}


# ---------------------------------------------------------------- reset (demo rows only)

def delete_demo(conn) -> dict:
    users = [r["ref_id"] for r in conn.execute("SELECT ref_id FROM demo_registry WHERE kind='user'").fetchall()]
    schools_ = [r["ref_id"] for r in conn.execute(
        "SELECT r.ref_id FROM demo_registry r JOIN schools s ON s.id=r.ref_id WHERE r.kind='school' AND s.is_demo=1").fetchall()]
    U, S = users or [0], schools_ or [0]
    u, s = ",".join("?" * len(U)), ",".join("?" * len(S))
    students = [r[0] for r in conn.execute(f"SELECT student_id FROM learner_links WHERE user_id IN ({u})", U).fetchall()] or [0]
    st = ",".join("?" * len(students))
    cases = [r[0] for r in conn.execute(f"SELECT id FROM cases WHERE student_id IN ({st})", students).fetchall()] or [0]
    cs = ",".join("?" * len(cases))
    classes = [r[0] for r in conn.execute(f"SELECT id FROM classes WHERE school_id IN ({s})", S).fetchall()] or [0]
    cl = ",".join("?" * len(classes))
    E = ",".join("?" * len(DEMO_EMAILS))
    steps = [
        (f"DELETE FROM responses WHERE student_id IN ({st}) OR assessment_id IN (SELECT id FROM assessments WHERE case_id IN ({cs}))", students + cases),
        *[(f"DELETE FROM {t} WHERE case_id IN ({cs})", cases) for t in
          ("agent_runs", "teacher_overrides", "lessons", "plans", "gaps", "case_topics", "assessments")],
        (f"DELETE FROM cases WHERE id IN ({cs})", cases),
        (f"DELETE FROM skill_mastery WHERE student_id IN ({st})", students),
        (f"DELETE FROM learner_links WHERE user_id IN ({u})", U),
        (f"DELETE FROM students WHERE id IN ({st})", students),
        (f"DELETE FROM access_log WHERE viewer_user_id IN ({u}) OR subject_user_id IN ({u})", U + U),
        (f"DELETE FROM share_grants WHERE owner_user_id IN ({u}) OR grantee_user_id IN ({u})", U + U),
        (f"DELETE FROM consent_records WHERE student_user_id IN ({u}) OR given_by_user_id IN ({u})", U + U),
        (f"DELETE FROM parent_student_links WHERE parent_user_id IN ({u}) OR student_user_id IN ({u})", U + U),
        (f"DELETE FROM teacher_class_assignments WHERE teacher_user_id IN ({u}) OR class_id IN ({cl})", U + classes),
        (f"DELETE FROM class_enrollments WHERE student_user_id IN ({u}) OR class_id IN ({cl})", U + classes),
        (f"DELETE FROM referral_codes WHERE school_id IN ({s}) OR created_by IN ({u})", S + U),
        (f"DELETE FROM school_memberships WHERE user_id IN ({u}) OR school_id IN ({s})", U + S),
        (f"UPDATE student_profiles SET school_id=NULL WHERE school_id IN ({s}) AND user_id NOT IN ({u})", S + U),
        *[(f"DELETE FROM {t} WHERE user_id IN ({u})", U) for t in
          ("student_profiles", "parent_profiles", "teacher_profiles", "auth_sessions")],
        (f"DELETE FROM email_tokens WHERE user_id IN ({u}) OR email IN ({E})", U + DEMO_EMAILS),
        (f"DELETE FROM email_outbox WHERE to_email IN ({E})", DEMO_EMAILS),
        (f"DELETE FROM classes WHERE id IN ({cl})", classes),
        (f"DELETE FROM schools WHERE id IN ({s}) AND is_demo=1", S),
        (f"DELETE FROM users WHERE id IN ({u})", U),
        ("DELETE FROM demo_registry", []),
    ]
    for sql, args in steps:
        conn.execute(sql, args)
    return {"users": len(users), "schools": len(schools_), "cases": len([x for x in cases if x])}


# ---------------------------------------------------------------- entry points

def seed(activity: bool = True) -> dict:
    with TestClient(app) as c:
        c.event_hooks["response"].append(lambda r: c.cookies.clear())   # use explicit tokens, not cookies
        with db.transaction() as conn:
            if conn.execute("SELECT 1 FROM demo_registry LIMIT 1").fetchone():
                raise SystemExit("Demo accounts already exist. Use: python scripts/demo.py reset")
            clash = _conflicts(conn)
            if clash:
                raise SystemExit(f"Stopped: demo usernames/emails are already used by non-demo accounts {clash}. "
                                 "Nothing was changed.")
        acc = create_accounts(c)
        act = create_activity(c, acc["teacher_token"]) if activity else {}
    return {"class_code": acc["code"], **act}


def reset() -> dict:
    with db.transaction() as conn:
        gone = delete_demo(conn)
    return {"deleted": gone, **seed()}


def status() -> list:
    with db.transaction() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT r.slug, u.full_name, u.role, u.status FROM demo_registry r JOIN users u ON u.id=r.ref_id "
            "WHERE r.kind='user' ORDER BY r.slug").fetchall()]


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "seed":
        print("Demo created:", seed("--no-activity" not in sys.argv))
    elif cmd == "reset":
        print("Demo reset:", reset())
    elif cmd == "status":
        rows = status()
        print("\n".join(f"{r['slug']:8} {r['full_name']:15} {r['role']:12} {r['status']}" for r in rows) or "No demo accounts.")
    else:
        raise SystemExit(__doc__)
    if cmd in ("seed", "reset"):
        print(f"Log in at /#/login with the usernames/emails in docs/DEMO_SCRIPT.md (password {PW}), "
              "or set ELEVIA_DEMO_MODE=1 for one-click demo login.")


if __name__ == "__main__":
    main()
