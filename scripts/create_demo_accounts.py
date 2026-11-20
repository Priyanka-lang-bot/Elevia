"""Create demo login accounts for every ELEVIA role, using the REAL registration routes.

    python scripts/create_demo_accounts.py            (uses the database in .env / ELEVIA_DB_PATH)

Nothing is hardcoded in the app: this script just fills in the normal sign-up, consent, invitation and
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


def main():
    with TestClient(app) as c:
        c.event_hooks["response"].append(lambda r: c.cookies.clear())  # use explicit tokens, not cookies
        with db.transaction() as conn:
            if conn.execute("SELECT 1 FROM users WHERE email IN (?,?)", (ADMIN, LEARNER)).fetchone():
                sys.exit("Demo accounts already exist in this database. Use a fresh database (delete elevia.db) to recreate them.")
            out = schools.create_school(conn, name="Sunrise Demo School", admin_email=ADMIN, state="Maharashtra",
                                        district="Pune", is_demo=True)
        admin = ok(c.post("/invites/accept", json={
            "token": token_from_outbox(ADMIN), "full_name": "Demo Admin", "password": PW}), "admin invite")["token"]
        cls = ok(c.post("/school/classes", json={"grade": 5, "division": "A", "academic_year": "2026-27"}, headers=H(admin)), "class")
        ok(c.post("/school/teachers/invite", json={"email": TEACHER}, headers=H(admin)), "teacher invite")
        t = ok(c.post("/invites/accept", json={"token": token_from_outbox(TEACHER), "full_name": "Demo Teacher",
                                               "password": PW}), "teacher accept")
        ok(c.post("/school/assignments", json={"teacher_id": t["user"]["id"], "class_id": cls["id"],
                                               "can_create_codes": True}, headers=H(admin)), "assign teacher")
        code = ok(c.post("/school/codes", json={"class_id": cls["id"], "expires_days": 60, "max_uses": 30},
                         headers=H(t["token"])), "referral code")
        code_text = code.get("code") or code
        # school student (needs parent consent unless the school handles it; the script does the parent step)
        sk = ok(c.post("/auth/register/school-student", json={
            "full_name": "Arjun Demo", "date_of_birth": years_ago(10), "username": SCHOOLKID, "password": PW,
            "parent_name": "Demo Parent Two", "parent_email": PARENT2, "code": code_text}), "school student")
        ok(c.post("/consent/accept", json={"token": token_from_outbox(PARENT2), "is_parent_or_guardian": True,
                                           "is_adult": True, "agree_purposes": True,
                                           "permissions": ["view_progress", "view_assessments"],
                                           "full_name": "Demo Parent Two", "password": PW}), "school parent consent")
        with db.transaction() as conn:
            enr = conn.execute("SELECT id FROM class_enrollments WHERE status='pending'").fetchone()
        if enr:
            ok(c.post(f"/school/enrollments/{enr['id']}/approve", headers=H(t["token"])), "approve enrolment")
        # individual child + parent
        ok(c.post("/auth/register/student", json={
            "full_name": "Riya Demo", "date_of_birth": years_ago(12), "username": CHILD, "password": PW,
            "parent_name": "Demo Parent", "parent_email": PARENT1}), "individual child")
        ok(c.post("/consent/accept", json={"token": token_from_outbox(PARENT1), "is_parent_or_guardian": True,
                                           "is_adult": True, "agree_purposes": True,
                                           "permissions": ["view_progress", "view_assessments", "view_activity"],
                                           "full_name": "Demo Parent", "password": PW}), "parent consent")
        # independent learner
        ok(c.post("/auth/register/learner", json={"full_name": "Demo Learner", "date_of_birth": years_ago(25),
                                                  "email": LEARNER, "password": PW, "accept_terms": True}), "learner")
        ok(c.post("/auth/verify-email", json={"token": token_from_outbox(LEARNER)}), "learner verify")
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
