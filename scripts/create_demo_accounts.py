"""Create demo login accounts for every ELEVIA role, using the REAL registration routes.

    python scripts/create_demo_accounts.py                 (uses the database in .env / ELEVIA_DB_PATH)
    python scripts/create_demo_accounts.py --with-activity (also gives Arjun scripted learning activity)

The people are fictional demo characters. Nothing is hardcoded in the app: this script just fills in the normal sign-up, consent, invitation and
approval steps for you, so each account goes through the same checks a real user would. It refuses to
run twice on the same database. The demo password below is for LOCAL TESTING ONLY, never use it on a
live deployment.
"""
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from backend import db  # noqa: E402
from backend.accounts import schools  # noqa: E402
from backend.main import app  # noqa: E402

PW = "Demo-Pass-2026!"
ADMIN, TEACHER = "demo.admin@example.com", "demo.teacher@example.com"
LEARNER, PARENT1, PARENT2 = "demo.learner@example.com", "demo.parent@example.com", "demo.parent2@example.com"
CHILD, SCHOOLKID = "riya.demo", "arjun.demo"


def years_ago(n):
    t = date.today()
    return t.replace(year=t.year - n, day=min(t.day, 28)).isoformat()


def H(tok):
    return {"Authorization": f"Bearer {tok}"}


def token_from_outbox(to_email):
    with db.transaction() as c:
        row = c.execute("SELECT body FROM email_outbox WHERE to_email=? ORDER BY id DESC LIMIT 1", (to_email,)).fetchone()
    return re.search(r"token=([A-Za-z0-9_\-]+)", row["body"]).group(1)


def ok(r, what):
    if r.status_code >= 300:
        sys.exit(f"FAILED at {what}: {r.status_code} {r.text}")
    return r.json()


def _answer_all(c, h, st, answers=None, wrong=False):
    from backend.content import questions
    from backend.engine import correct_answer_text
    out = None
    for item in st["assessment"]["questions"]:
        if item["answered"]:
            continue
        q = questions()[item["id"]]
        a = (answers or {}).get(q["id"]) or ("1/100" if wrong else correct_answer_text(q))
        out = ok(c.post("/learn/answer", json={"assessment_id": st["assessment"]["id"], "question_id": q["id"],
                                               "answer": a}, headers=h), "answer")
    return out["state"]


def demo_activity(c):
    """Scripted answers run through the REAL workflow (like seed.py), so the teacher view has data:
    Arjun: decimals journey completed (gap confirmed, taught, retest passed), and a fractions case whose
    double-check was inconclusive, so it waits for the teacher's review."""
    tok = ok(c.post("/auth/login", json={"identifier": SCHOOLKID, "password": PW}), "login arjun")["token"]
    h = H(tok)
    st = ok(c.post("/learn/start", json={"topic_id": "decimals"}, headers=h), "decimals start")
    st = _answer_all(c, h, st, {"DEC-DA1": "0.25", "DEC-DA2": "0.65"})            # 'longer is bigger' twice
    st = _answer_all(c, h, st, {"DEC-VDPV1": "0.36", "DEC-VDPV2": "0.55"})        # same mistake again -> confirmed
    st = _answer_all(c, h, st)                                                     # practice
    if st["phase"] == "learn":
        st = ok(c.post("/learn/practice/finish", json={"assessment_id": st["assessment"]["id"]}, headers=h), "finish")
    st = ok(c.post("/learn/retest/start", json={"early": True, "topic_id": "decimals"}, headers=h), "retest")
    st = _answer_all(c, h, st)
    st = ok(c.post("/learn/start", json={"topic_id": "fractions"}, headers=h), "fractions start")
    st = _answer_all(c, h, st, {"DA3": "2/5"})
    st = _answer_all(c, h, st, {"CD-V1": "3/4"})                                   # mixed evidence -> teacher review
    return st["phase"]


def main():
    with_activity = "--with-activity" in sys.argv
    with TestClient(app) as c:
        c.event_hooks["response"].append(lambda r: c.cookies.clear())  # use explicit tokens, not cookies
        with db.transaction() as conn:
            if conn.execute("SELECT 1 FROM users WHERE email IN (?,?)", (ADMIN, LEARNER)).fetchone():
                sys.exit("Demo accounts already exist in this database. Use a fresh database (delete elevia.db) to recreate them.")
            out = schools.create_school(conn, name="Sunrise Demo School", admin_email=ADMIN, state="Maharashtra",
                                        district="Pune", is_demo=True)
        admin = ok(c.post("/invites/accept", json={
            "token": token_from_outbox(ADMIN), "full_name": "Kavita Menon", "password": PW}), "admin invite")["token"]
        cls = ok(c.post("/school/classes", json={"grade": 5, "division": "A", "academic_year": "2026-27"}, headers=H(admin)), "class")
        ok(c.post("/school/teachers/invite", json={"email": TEACHER}, headers=H(admin)), "teacher invite")
        t = ok(c.post("/invites/accept", json={"token": token_from_outbox(TEACHER), "full_name": "Meera Iyer",
                                               "password": PW}), "teacher accept")
        ok(c.post("/school/assignments", json={"teacher_id": t["user"]["id"], "class_id": cls["id"],
                                               "can_create_codes": True}, headers=H(admin)), "assign teacher")
        code = ok(c.post("/school/codes", json={"class_id": cls["id"], "expires_days": 60, "max_uses": 30},
                         headers=H(t["token"])), "referral code")
        code_text = code.get("code") or code
        # school student (needs parent consent unless the school handles it; the script does the parent step)
        sk = ok(c.post("/auth/register/school-student", json={
            "full_name": "Arjun Patel", "date_of_birth": years_ago(10), "username": SCHOOLKID, "password": PW,
            "parent_name": "Raj Patel", "parent_email": PARENT2, "code": code_text}), "school student")
        ok(c.post("/consent/accept", json={"token": token_from_outbox(PARENT2), "is_parent_or_guardian": True,
                                           "is_adult": True, "agree_purposes": True,
                                           "permissions": ["view_progress", "view_assessments"],
                                           "full_name": "Raj Patel", "password": PW}), "school parent consent")
        with db.transaction() as conn:
            enr = conn.execute("SELECT id FROM class_enrollments WHERE status='pending'").fetchone()
        if enr:
            ok(c.post(f"/school/enrollments/{enr['id']}/approve", headers=H(t["token"])), "approve enrolment")
        # individual child + parent
        ok(c.post("/auth/register/student", json={
            "full_name": "Riya Sharma", "date_of_birth": years_ago(12), "username": CHILD, "password": PW,
            "parent_name": "Sunita Sharma", "parent_email": PARENT1}), "individual child")
        ok(c.post("/consent/accept", json={"token": token_from_outbox(PARENT1), "is_parent_or_guardian": True,
                                           "is_adult": True, "agree_purposes": True,
                                           "permissions": ["view_progress", "view_assessments", "view_activity"],
                                           "full_name": "Sunita Sharma", "password": PW}), "parent consent")
        # independent learner
        ok(c.post("/auth/register/learner", json={"full_name": "Ananya Rao", "date_of_birth": years_ago(25),
                                                  "email": LEARNER, "password": PW, "accept_terms": True}), "learner")
        ok(c.post("/auth/verify-email", json={"token": token_from_outbox(LEARNER)}), "learner verify")
        activity = demo_activity(c) if with_activity else None
    print(("Scripted activity added for Arjun (decimals finished; fractions waiting for teacher review).\n"
           if activity else ""), end="")
    print(f"""
Demo accounts created. Log in at http://localhost:8000/#/login   (password for ALL: {PW})

  Role                  Log in with                 Notes
  School admin          {ADMIN}      invited via create_school; manages classes/teachers/codes
  Teacher               {TEACHER}    assigned to Class 5 A; can create codes, approve students
  Individual student    {CHILD}                 12 years old; unlocked by parent consent (done)
  Parent                {PARENT1}     linked to Riya
  School student        {SCHOOLKID}                 joined with code {code_text}; parent: {PARENT2}
  Second parent         {PARENT2}    linked to Arjun
  Independent learner   {LEARNER}   email already verified
""")


if __name__ == "__main__":
    main()
