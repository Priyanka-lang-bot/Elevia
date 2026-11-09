"""Users, sessions, login, email verification, password reset, rate limits."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from ..db import now_iso, row_to_dict
from . import emailer
from .errors import AccountError
from .security import (burn_time, check_password, clean_email, hash_password, new_token,
                       token_hash, verify_password)

SESSION_DAYS = 7
SESSION_IDLE_HOURS = 24
LOGIN_FAILS, LOGIN_WINDOW_MIN = 5, 15

TOKEN_HOURS = {"verify_email": 48, "reset_password": 1, "parent_consent": 72,
               "teacher_invite": 168, "admin_invite": 168, "share_invite": 168}

ROLE_LABELS = {"student": "Student", "learner": "Independent learner", "parent": "Parent / guardian",
               "teacher": "Teacher", "school_admin": "School admin", "platform_admin": "ELEVIA admin"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(dt: datetime) -> str:
    return dt.isoformat()


# ---------------------------------------------------------------- rate limiting

def rate_limited(conn, key: str, limit: int, window_min: int) -> bool:
    since = iso(utcnow() - timedelta(minutes=window_min))
    n = conn.execute("SELECT COUNT(*) FROM rate_events WHERE key=? AND created_at>=?", (key, since)).fetchone()[0]
    return n >= limit


def record_event(conn, key: str) -> None:
    """Committed in its own transaction, so a failed attempt still counts even though the
    request's own transaction is rolled back when the error is raised."""
    from .. import db
    if conn.in_transaction:  # this request already holds the write lock; record with it
        conn.execute("INSERT INTO rate_events (key, created_at) VALUES (?,?)", (key, now_iso()))
        return
    with db.transaction() as own:
        own.execute("INSERT INTO rate_events (key, created_at) VALUES (?,?)", (key, now_iso()))
        own.execute("DELETE FROM rate_events WHERE created_at < ?", (iso(utcnow() - timedelta(days=1)),))


def clear_events(conn, key: str) -> None:
    conn.execute("DELETE FROM rate_events WHERE key=?", (key,))


# ---------------------------------------------------------------- users

def get_user(conn, user_id: int) -> Optional[dict]:
    return row_to_dict(conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())


def public_user(u: dict) -> dict:
    return {k: u[k] for k in ("id", "role", "email", "username", "full_name", "status", "created_at")} | {
        "role_label": ROLE_LABELS[u["role"]], "email_verified": bool(u.get("email_verified_at"))}


def email_taken(conn, email: Optional[str]) -> bool:
    return bool(email) and conn.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone() is not None


def username_taken(conn, username: Optional[str]) -> bool:
    return bool(username) and conn.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone() is not None


def insert_user(conn, *, role: str, full_name: str, password: str, status: str, email: Optional[str] = None,
                username: Optional[str] = None, dob: Optional[str] = None, email_verified: bool = False) -> int:
    if email_taken(conn, email):
        raise AccountError("An account with this email already exists. Try logging in instead.", 409,
                           field="email", code="email_taken")
    if username_taken(conn, username):
        raise AccountError("That username is taken. Please choose another.", 409, field="username",
                           code="username_taken")
    t = now_iso()
    cur = conn.execute(
        "INSERT INTO users (role, email, email_verified_at, username, password_hash, full_name, date_of_birth, "
        "status, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (role, email, t if email_verified else None, username, hash_password(password), full_name, dob,
         status, t, t))
    return cur.lastrowid


def set_status(conn, user_id: int, status: str) -> None:
    conn.execute("UPDATE users SET status=?, updated_at=? WHERE id=?", (status, now_iso(), user_id))


# ---------------------------------------------------------------- emailed tokens

def issue_token(conn, purpose: str, email: str, user_id: Optional[int] = None, payload: Optional[dict] = None) -> str:
    raw = new_token()
    exp = iso(utcnow() + timedelta(hours=TOKEN_HOURS[purpose]))
    conn.execute(
        "INSERT INTO email_tokens (token_hash, purpose, user_id, email, payload, created_at, expires_at) "
        "VALUES (?,?,?,?,?,?,?)", (token_hash(raw), purpose, user_id, email, json.dumps(payload or {}), now_iso(), exp))
    return raw


def peek_token(conn, raw: str, purpose: str) -> dict:
    """Return a valid, unused token row (with payload parsed) or raise one generic error."""
    row = row_to_dict(conn.execute("SELECT * FROM email_tokens WHERE token_hash=? AND purpose=?",
                                   (token_hash(raw or ""), purpose)).fetchone())
    if row is None or row["used_at"] or row["expires_at"] < now_iso():
        raise AccountError("This link is invalid or has expired. Please ask for a new one.", 400, code="bad_token")
    row["payload"] = json.loads(row["payload"] or "{}")
    return row


def consume_token(conn, token_id: int) -> None:
    conn.execute("UPDATE email_tokens SET used_at=? WHERE id=?", (now_iso(), token_id))


def invalidate_tokens(conn, purpose: str, *, user_id: Optional[int] = None, email: Optional[str] = None) -> None:
    if user_id is not None:
        conn.execute("UPDATE email_tokens SET used_at=? WHERE purpose=? AND user_id=? AND used_at IS NULL",
                     (now_iso(), purpose, user_id))
    if email is not None:
        conn.execute("UPDATE email_tokens SET used_at=? WHERE purpose=? AND email=? AND used_at IS NULL",
                     (now_iso(), purpose, email))


# ---------------------------------------------------------------- sessions

def create_session(conn, user_id: int) -> str:
    raw = new_token()
    t = utcnow()
    conn.execute("INSERT INTO auth_sessions (token_hash, user_id, created_at, expires_at, last_seen_at) "
                 "VALUES (?,?,?,?,?)", (token_hash(raw), user_id, iso(t), iso(t + timedelta(days=SESSION_DAYS)), iso(t)))
    return raw


def user_for_session(conn, raw: str) -> Optional[dict]:
    if not raw:
        return None
    s = row_to_dict(conn.execute("SELECT * FROM auth_sessions WHERE token_hash=?", (token_hash(raw),)).fetchone())
    now = utcnow()
    if (s is None or s["revoked_at"] or s["expires_at"] < iso(now)
            or s["last_seen_at"] < iso(now - timedelta(hours=SESSION_IDLE_HOURS))):
        return None
    conn.execute("UPDATE auth_sessions SET last_seen_at=? WHERE id=?", (iso(now), s["id"]))
    return get_user(conn, s["user_id"])


def revoke_session(conn, raw: str) -> None:
    conn.execute("UPDATE auth_sessions SET revoked_at=? WHERE token_hash=? AND revoked_at IS NULL",
                 (now_iso(), token_hash(raw or "")))


def revoke_all_sessions(conn, user_id: int) -> None:
    conn.execute("UPDATE auth_sessions SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL", (now_iso(), user_id))


# ---------------------------------------------------------------- login

GENERIC_LOGIN_ERROR = "That email/username and password don't match. Please try again."


def login(conn, identifier: str, password: str) -> dict:
    ident = (identifier or "").strip().lower()
    if not ident or not password:
        raise AccountError("Enter your email or username and your password.", 400)
    key = f"login:{ident}"
    if rate_limited(conn, key, LOGIN_FAILS, LOGIN_WINDOW_MIN):
        raise AccountError("Too many attempts. Please wait 15 minutes and try again.", 429, code="locked")
    col = "email" if "@" in ident else "username"
    user = row_to_dict(conn.execute(f"SELECT * FROM users WHERE {col}=?", (ident,)).fetchone())
    if user is None:
        burn_time(password)
        record_event(conn, key)
        raise AccountError(GENERIC_LOGIN_ERROR, 401, code="bad_credentials")
    if not verify_password(password, user["password_hash"]):
        record_event(conn, key)
        raise AccountError(GENERIC_LOGIN_ERROR, 401, code="bad_credentials")
    if user["status"] == "suspended":
        raise AccountError("This account is paused. If you're a student, ask your parent or school.", 403,
                           code="suspended")
    clear_events(conn, key)
    return {"token": create_session(conn, user["id"]), "user": public_user(user)}


# ---------------------------------------------------------------- email verification

def send_verification(conn, user: dict) -> None:
    invalidate_tokens(conn, "verify_email", user_id=user["id"])
    raw = issue_token(conn, "verify_email", user["email"], user["id"])
    subj, body = emailer.verify_email(user["full_name"], emailer.link("verify", raw))
    emailer.send(conn, user["email"], subj, body)


def resend_verification(conn, user: dict) -> None:
    if user["status"] != "pending_verification" or not user["email"]:
        raise AccountError("This account doesn't need email verification.", 409)
    key = f"resend-verify:{user['id']}"
    if rate_limited(conn, key, 3, 60):
        raise AccountError("Please wait a while before asking for another email.", 429)
    record_event(conn, key)
    send_verification(conn, user)


def verify_email(conn, raw: str) -> dict:
    tok = peek_token(conn, raw, "verify_email")
    user = get_user(conn, tok["user_id"])
    if user is None:
        raise AccountError("This link is invalid or has expired. Please ask for a new one.", 400, code="bad_token")
    consume_token(conn, tok["id"])
    conn.execute("UPDATE users SET email_verified_at=?, updated_at=? WHERE id=?", (now_iso(), now_iso(), user["id"]))
    if user["status"] == "pending_verification":
        set_status(conn, user["id"], "active")
    return public_user(get_user(conn, user["id"]))


# ---------------------------------------------------------------- password reset

def forgot_password(conn, email: str) -> None:
    """Always succeeds from the caller's view, so it can't reveal whether an email is registered."""
    e = clean_email(email)
    key = f"forgot:{e}"
    if rate_limited(conn, key, 3, 60):
        return
    record_event(conn, key)
    user = row_to_dict(conn.execute("SELECT * FROM users WHERE email=?", (e,)).fetchone())
    if user is None:
        return
    invalidate_tokens(conn, "reset_password", user_id=user["id"])
    raw = issue_token(conn, "reset_password", e, user["id"])
    subj, body = emailer.reset_password(user["full_name"], emailer.link("reset", raw))
    emailer.send(conn, e, subj, body)


def reset_password(conn, raw: str, new_password: str) -> None:
    tok = peek_token(conn, raw, "reset_password")
    user = get_user(conn, tok["user_id"])
    if user is None:
        raise AccountError("This link is invalid or has expired. Please ask for a new one.", 400, code="bad_token")
    check_password(new_password, username=user["username"], email=user["email"])
    consume_token(conn, tok["id"])
    conn.execute("UPDATE users SET password_hash=?, updated_at=? WHERE id=?",
                 (hash_password(new_password), now_iso(), user["id"]))
    revoke_all_sessions(conn, user["id"])
    clear_events(conn, f"login:{(user['email'] or '').lower()}")
