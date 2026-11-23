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

import os

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from . import db
from .accounts import core
from .accounts.errors import AccountError

router = APIRouter(prefix="/demo")

# What each card says. Names match the people the seed creates (fictional).
# Only STUDENT accounts can be opened with one click. The teacher, parent and admin demo accounts still exist
# (the seed creates them so the student data has a real class, consent and teacher decisions behind it), but
# they are reached with a normal password login, so no staff or parent account is publicly one click away.
PROFILES = [
    {"slug": "fresh", "name": "Ananya Rao", "role": "New student", "badge": "Start from scratch",
     "explore": "No history yet. Pick a topic, make a mistake on purpose and watch ELEVIA check it "
                "before it teaches anything."},
    {"slug": "riya", "name": "Riya Sharma", "role": "Student", "badge": "Grade 6 · Class 6 A",
     "explore": "A student with history: mastered skills, a failed-then-passed retest, a lesson in progress "
                "and a retest booked."},
    {"slug": "arjun", "name": "Arjun Patel", "role": "Student", "badge": "Grade 6 · Class 6 A",
     "explore": "A student who is finding things harder: open gaps, a failed retest, a teacher's note and a "
                "case waiting for his teacher."},
]
SLUGS = {p["slug"] for p in PROFILES}
STAFF_SLUGS = {"teacher", "parent", "parent2", "admin"}   # registry entries that are never one-click


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


@router.get("/accounts")
def accounts():
    if not enabled():
        return {"enabled": False, "accounts": []}
    with db.transaction() as conn:
        have = registry_users(conn)
    return {"enabled": True, "ready": all(p["slug"] in have for p in PROFILES),
            "accounts": [{**p, "available": p["slug"] in have} for p in PROFILES]}


@router.post("/login")
def demo_login(body: DemoLogin, request: Request, response: Response):
    from .accounts.routes import _with_session  # same cookie handling as the password login
    if not enabled():
        raise AccountError("Not found.", 404)
    if body.slug in STAFF_SLUGS:
        raise AccountError("Teacher, parent and admin demo accounts use a normal password login.", 403,
                           code="demo_student_only")
    if body.slug not in SLUGS:
        raise AccountError("Unknown demo account.", 400)
    ip = (request.headers.get("x-forwarded-for", "").split(",")[0].strip()
          or (request.client.host if request.client else "unknown"))
    key = f"demo-login:{ip}"
    with db.transaction() as conn:
        if core.rate_limited(conn, key, 60, 10):
            raise AccountError("Too many demo logins from here. Please wait a few minutes.", 429)
        core.record_event(conn, key)
        uid = registry_users(conn).get(body.slug)
        user = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone() if uid else None
        if user is None:
            raise AccountError("The demo accounts haven't been set up on this server yet.", 409, code="demo_not_ready")
        if user["status"] != "active":
            raise AccountError("This demo account needs a reset (scripts/demo.py reset).", 409, code="demo_needs_reset")
        result = {"token": core.create_session(conn, user["id"]), "user": core.public_user(dict(user))}
    return _with_session(request, response, result)
