"""Demo mode for judges: one-click login to fictional demo accounts.

Safety model
- Off unless the server has ELEVIA_DEMO_MODE=1. With it off, /demo/login returns 404.
- Only accounts listed in `demo_registry` (written by scripts/demo.py when it creates them) can be used.
  A real user can never be logged into, even one with a demo-looking username.
- It issues a normal session (HttpOnly cookie), exactly like a password login. No password is ever sent
  to the browser or stored in the page.
- Rate-limited per IP. A few actions that would break the shared demo for the next judge, or send real
  emails to arbitrary addresses, are refused for demo accounts (see `refuse_for_demo`).
- Reset (scripts/demo.py reset) deletes only rows that belong to registry-listed users and schools.
"""
from __future__ import annotations

import hmac
import os

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from . import db
from .accounts import core
from .accounts.errors import AccountError

router = APIRouter(prefix="/demo")

# What each card says. Names match the people the seed creates (fictional).
# Student accounts open with one click. The teacher demo opens only with the judges' access code
# (ELEVIA_DEMO_TEACHER_CODE, a server secret, never in the repository or the page). Parent and admin demo
# accounts are never one-click: they exist so the student data has real consent and a real school behind it.
PROFILES = [
    {"slug": "riya", "name": "Riya Sharma", "role": "Student · DEMO-09-001", "badge": "Grade 9 · Class 9 A · 2026-27",
     "explore": "Six months of history across five subjects: mastered skills, retests failed then passed, a lesson "
                "in progress, a retest due and a case waiting for her teacher."},
    {"slug": "fresh", "name": "Dev Kapoor", "role": "New learner", "badge": "No history yet",
     "explore": "Start from nothing. Pick a topic, make a mistake on purpose and watch ELEVIA check it before it "
                "teaches anything."},
    {"slug": "arjun", "name": "Arjun Patel", "role": "Student · DEMO-09-002", "badge": "Grade 9 · Class 9 A · 2026-27",
     "explore": "Finding maths hard: repeated failed retests on integers, a teacher's note and a case waiting for "
                "his teacher."},
]
TEACHER_PROFILE = {"slug": "teacher", "name": "Ananya Mehta", "role": "Class 9 teacher",
                   "badge": "ELEVIA Demonstration School",
                   "explore": "The class overview, the review queue, Riya's six-month record and the evidence behind "
                              "every gap. Confirm or reject a case with a reason and see it in the history."}
SLUGS = {p["slug"] for p in PROFILES}
STAFF_SLUGS = {"parent", "parent2", "parent3", "parent4", "parent5", "admin"}   # never one-click


def teacher_code() -> str:
    """The judges' access code for the teacher demo, or '' when the teacher demo is off."""
    code = os.getenv("ELEVIA_DEMO_TEACHER_CODE", "").strip()
    return code if len(code) >= 8 else ""


def enabled() -> bool:
    return os.getenv("ELEVIA_DEMO_MODE", "").strip().lower() in ("1", "true", "yes", "on")


def registry_users(conn) -> dict[str, int]:
    return {r["slug"]: r["ref_id"] for r in conn.execute(
        "SELECT slug, ref_id FROM demo_registry WHERE kind='user'").fetchall()}


def is_demo_user(conn, user_id: int) -> bool:
    return conn.execute("SELECT 1 FROM demo_registry WHERE kind='user' AND ref_id=?", (user_id,)).fetchone() is not None


def refuse_for_demo(conn, user: dict, what: str) -> None:
    if is_demo_user(conn, user["id"]):
        raise AccountError(f"This is a shared demo account, so {what} is turned off. Everything else works.", 403,
                           code="demo_locked")


class DemoLogin(BaseModel):
    slug: str = Field(max_length=20)
    access_code: str = Field(default="", max_length=100)


@router.get("/accounts")
def accounts():
    if not enabled():
        return {"enabled": False, "accounts": []}
    with db.transaction() as conn:
        have = registry_users(conn)
    return {"enabled": True, "ready": all(p["slug"] in have for p in PROFILES),
            "accounts": [{**p, "available": p["slug"] in have} for p in PROFILES],
            # the teacher card says whether an access code will work; the code itself is never sent
            "teacher": {**TEACHER_PROFILE, "available": bool(teacher_code()) and "teacher" in have}}


@router.post("/login")
def demo_login(body: DemoLogin, request: Request, response: Response):
    from .accounts.routes import _with_session  # same cookie handling as the password login
    if not enabled():
        raise AccountError("Not found.", 404)
    if body.slug in STAFF_SLUGS:
        raise AccountError("Parent and admin demo accounts use a normal password login.", 403,
                           code="demo_student_only")
    if body.slug not in SLUGS and body.slug != "teacher":
        raise AccountError("Unknown demo account.", 400)
    ip = (request.headers.get("x-forwarded-for", "").split(",")[0].strip()
          or (request.client.host if request.client else "unknown"))
    key, bad = f"demo-login:{ip}", f"demo-code:{ip}"
    # Attempts are recorded in their own transaction, so a refused attempt still counts towards the limits.
    with db.transaction() as conn:
        too_many = core.rate_limited(conn, key, 60, 10)
        too_many_codes = body.slug == "teacher" and core.rate_limited(conn, bad, 10, 10)
        code = teacher_code() if body.slug == "teacher" else ""
        code_ok = bool(code) and hmac.compare_digest(body.access_code.strip().encode(), code.encode())
        if not too_many:
            core.record_event(conn, key)
        if body.slug == "teacher" and code and not code_ok and not too_many_codes:
            core.record_event(conn, bad)
    if too_many:
        raise AccountError("Too many demo logins from here. Please wait a few minutes.", 429)
    if body.slug == "teacher":
        if not code:
            raise AccountError("The teacher demo isn't switched on for this server.", 403, code="demo_teacher_off")
        if too_many_codes:
            raise AccountError("Too many wrong access codes. Please wait a few minutes.", 429)
        if not code_ok:
            raise AccountError("That access code isn't right.", 403, code="demo_bad_code")
    with db.transaction() as conn:
        uid = registry_users(conn).get(body.slug)
        user = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone() if uid else None
        if user is None:
            raise AccountError("The demo accounts haven't been set up on this server yet.", 409, code="demo_not_ready")
        if user["status"] != "active":
            raise AccountError("This demo account needs a reset (scripts/demo.py reset).", 409, code="demo_needs_reset")
        result = {"token": core.create_session(conn, user["id"]), "user": core.public_user(dict(user))}
    return _with_session(request, response, result)
