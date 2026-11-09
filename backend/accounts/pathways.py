"""Pathway 1 (individual student + parent consent), pathway 3 (independent learner),
parent controls, and the shared "what should this user do next" logic."""
from __future__ import annotations

import json
from datetime import timedelta
from typing import Optional

from ..db import now_iso, row_to_dict, rows_to_dicts
from . import core, emailer
from .errors import AccountError
from .security import (age_on, check_password, clean_email, clean_name, clean_username, parse_dob,
                       verify_password)

NOTICE_VERSION = "2026-11-draft-1"
CONSENT_METHOD = "email_link+declaration"  # not DPDP Rule 10-grade verification; see architecture doc
REQUIRED_PURPOSES = {
    "account": "Create and run the student's ELEVIA account",
    "learning_data": "Store the student's answers and progress to find learning gaps and plan lessons",
}
PARENT_PERMISSIONS = {
    "view_progress": "See progress and skills",
    "view_assessments": "See assessment results",
    "view_activity": "See recent learning activity",
    "weekly_email": "Receive a weekly progress email",
    "share_with_school_teachers": "Let the child's school teachers see ELEVIA progress",
}
DEFAULT_PARENT_PERMISSIONS = ["view_progress", "view_assessments", "view_activity"]
UNCONSENTED_DAYS = 14
MIN_STUDENT_AGE = 5


def first_name(full_name: str) -> str:
    return full_name.split()[0]


# ---------------------------------------------------------------- shared validation

def validate_student_basics(full_name, dob, username, password, student_email):
    name = clean_name(full_name)
    d = parse_dob(dob)
    age = age_on(d)
    uname = clean_username(username)
    email = clean_email(student_email, required=False)
    check_password(password, username=uname, email=email)
    if age < MIN_STUDENT_AGE:
        raise AccountError(f"Students must be at least {MIN_STUDENT_AGE} years old.", 400, field="date_of_birth")
    return name, d, age, uname, email


def validate_parent_contact(parent_name, parent_email, student_email):
    pname = clean_name(parent_name, field="parent_name")
    pemail = clean_email(parent_email)
    if student_email and pemail == student_email:
        raise AccountError("The parent's email must be different from the student's.", 400, field="parent_email")
    return pname, pemail


def send_parent_invite(conn, student_id: int, student_name: str, parent_name: str, parent_email: str) -> None:
    core.invalidate_tokens(conn, "parent_consent", user_id=student_id)
    raw = core.issue_token(conn, "parent_consent", parent_email, student_id, {"parent_name": parent_name})
    subj, body = emailer.parent_consent(first_name(student_name), parent_name, emailer.link("consent", raw))
    emailer.send(conn, parent_email, subj, body)


# ---------------------------------------------------------------- pathway 1

def register_individual_student(conn, *, full_name, date_of_birth, username, password, parent_name,
                                parent_email, student_email=None) -> dict:
    purge_unconsented(conn)
    name, d, age, uname, email = validate_student_basics(full_name, date_of_birth, username, password, student_email)
    if age >= 18:
        raise AccountError("You're 18 or older, so please use the Independent Learner option.", 400,
                           field="date_of_birth", code="use_learner")
    pname, pemail = validate_parent_contact(parent_name, parent_email, email)
    uid = core.insert_user(conn, role="student", full_name=name, password=password, status="pending_consent",
                           email=email, username=uname, dob=d.isoformat())
    conn.execute("INSERT INTO student_profiles (user_id, pathway) VALUES (?, 'individual')", (uid,))
    send_parent_invite(conn, uid, name, pname, pemail)
    return {"token": core.create_session(conn, uid), "user": core.public_user(core.get_user(conn, uid))}


def resend_parent_invite(conn, student: dict, parent_name=None, parent_email=None) -> None:
    if student["role"] != "student" or student["status"] != "pending_consent":
        raise AccountError("No parent consent is waiting for this account.", 409)
    key = f"resend-consent:{student['id']}"
    if core.rate_limited(conn, key, 3, 60):
        raise AccountError("Please wait a while before sending another email.", 429)
    last = row_to_dict(conn.execute("SELECT * FROM email_tokens WHERE purpose='parent_consent' AND user_id=? "
                                    "ORDER BY id DESC LIMIT 1", (student["id"],)).fetchone())
    pname = clean_name(parent_name, field="parent_name") if parent_name else (
        json.loads(last["payload"]).get("parent_name") if last else None)
    pemail = clean_email(parent_email) if parent_email else (last["email"] if last else None)
    if not pname or not pemail:
        raise AccountError("Please enter your parent's name and email.", 400)
    if student["email"] and pemail == student["email"]:
        raise AccountError("The parent's email must be different from the student's.", 400, field="parent_email")
    core.record_event(conn, key)
    send_parent_invite(conn, student["id"], student["full_name"], pname, pemail)


def purge_unconsented(conn) -> int:
    cutoff = core.iso(core.utcnow() - timedelta(days=UNCONSENTED_DAYS))
    cur = conn.execute("DELETE FROM users WHERE role='student' AND status='pending_consent' AND created_at < ?",
                       (cutoff,))
    return cur.rowcount


# ---------------------------------------------------------------- parent consent

def consent_info(conn, raw: str) -> dict:
    tok = core.peek_token(conn, raw, "parent_consent")
    student = core.get_user(conn, tok["user_id"])
    if student is None or student["status"] != "pending_consent":
        raise AccountError("This link is invalid or has expired. Please ask for a new one.", 400, code="bad_token")
    has_account = conn.execute("SELECT role FROM users WHERE email=?", (tok["email"],)).fetchone()
    return {
        "child_first_name": first_name(student["full_name"]),
        "parent_name": tok["payload"].get("parent_name"),
        "parent_email": tok["email"],
        "parent_has_account": bool(has_account),
        "notice_version": NOTICE_VERSION,
        "purposes": REQUIRED_PURPOSES,
        "permissions": PARENT_PERMISSIONS,
        "default_permissions": DEFAULT_PARENT_PERMISSIONS,
        "expires_at": tok["expires_at"],
    }


def accept_consent(conn, raw: str, *, is_parent_or_guardian: bool, is_adult: bool, agree_purposes: bool,
                   permissions: list[str], actor: Optional[dict] = None, full_name: Optional[str] = None,
                   password: Optional[str] = None) -> dict:
    tok = core.peek_token(conn, raw, "parent_consent")
    student = core.get_user(conn, tok["user_id"])
    if student is None or student["status"] != "pending_consent":
        raise AccountError("This link is invalid or has expired. Please ask for a new one.", 400, code="bad_token")
    if not (is_parent_or_guardian and is_adult):
        raise AccountError("Only a parent or lawful guardian aged 18 or over can give consent.", 400,
                           field="declarations")
    if not agree_purposes:
        raise AccountError("Consent to the required purposes is needed to activate the account.", 400,
                           field="purposes")
    bad = set(permissions or []) - set(PARENT_PERMISSIONS)
    if bad:
        raise AccountError("Unknown permission requested.", 400, field="permissions")

    email = tok["email"]
    existing = row_to_dict(conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone())
    session_token = None
    if existing:
        if existing["role"] != "parent":
            raise AccountError("This email belongs to a different kind of ELEVIA account. Ask the student to use "
                               "another parent email.", 409, code="email_other_role")
        authed = (actor and actor["id"] == existing["id"]) or (password and verify_password(password, existing["password_hash"]))
        if not authed:
            raise AccountError("Please log in to your parent account to continue.", 401, code="login_required")
        parent_id = existing["id"]
        if not (actor and actor["id"] == existing["id"]):
            session_token = core.create_session(conn, parent_id)
        if not existing["email_verified_at"]:
            conn.execute("UPDATE users SET email_verified_at=? WHERE id=?", (now_iso(), parent_id))
    else:
        name = clean_name(full_name or tok["payload"].get("parent_name") or "")
        check_password(password or "", email=email)
        parent_id = core.insert_user(conn, role="parent", full_name=name, password=password, status="active",
                                     email=email, email_verified=True)  # the emailed link proves the address
        conn.execute("INSERT INTO parent_profiles (user_id) VALUES (?)", (parent_id,))
        session_token = core.create_session(conn, parent_id)

    perms = sorted(set(permissions or []))
    t = now_iso()
    conn.execute(
        "INSERT INTO parent_student_links (parent_user_id, student_user_id, status, permissions, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?) ON CONFLICT(parent_user_id, student_user_id) DO UPDATE SET status='active', "
        "permissions=excluded.permissions, updated_at=excluded.updated_at",
        (parent_id, student["id"], "active", json.dumps(perms), t, t))
    _consent_record(conn, student["id"], parent_id, "granted", perms,
                    {"is_parent_or_guardian": True, "is_adult": True})
    core.set_status(conn, student["id"], "active")
    core.consume_token(conn, tok["id"])
    core.invalidate_tokens(conn, "parent_consent", user_id=student["id"])
    return {"token": session_token, "user": core.public_user(core.get_user(conn, parent_id)),
            "child": {"id": student["id"], "first_name": first_name(student["full_name"])}}


def decline_consent(conn, raw: str) -> None:
    tok = core.peek_token(conn, raw, "parent_consent")
    student = core.get_user(conn, tok["user_id"])
    core.consume_token(conn, tok["id"])
    if student and student["status"] == "pending_consent":
        conn.execute("DELETE FROM users WHERE id=?", (student["id"],))  # nothing kept without consent


def _consent_record(conn, student_id, parent_id, action, perms, declarations):
    conn.execute(
        "INSERT INTO consent_records (student_user_id, given_by_user_id, action, purposes, permissions, "
        "notice_version, method, declarations, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (student_id, parent_id, action, json.dumps(sorted(REQUIRED_PURPOSES) if action != "withdrawn" else []),
         json.dumps(perms), NOTICE_VERSION, CONSENT_METHOD, json.dumps(declarations), now_iso()))


# ---------------------------------------------------------------- parent controls

def _active_link(conn, parent: dict, student_id: int) -> dict:
    if parent["role"] != "parent":
        raise AccountError("Only parent accounts can do this.", 403)
    link = row_to_dict(conn.execute("SELECT * FROM parent_student_links WHERE parent_user_id=? AND student_user_id=? "
                                    "AND status='active'", (parent["id"], student_id)).fetchone())
    if link is None:
        raise AccountError("Not found.", 404)
    return link


def list_children(conn, parent: dict) -> list[dict]:
    if parent["role"] != "parent":
        raise AccountError("Only parent accounts can do this.", 403)
    rows = rows_to_dicts(conn.execute(
        "SELECT l.*, u.full_name, u.status AS student_status FROM parent_student_links l JOIN users u "
        "ON u.id=l.student_user_id WHERE l.parent_user_id=? ORDER BY u.full_name", (parent["id"],)).fetchall())
    out = []
    for r in rows:
        history = rows_to_dicts(conn.execute(
            "SELECT action, permissions, notice_version, method, created_at FROM consent_records "
            "WHERE student_user_id=? AND given_by_user_id=? ORDER BY id", (r["student_user_id"], parent["id"])).fetchall())
        out.append({"student_id": r["student_user_id"], "full_name": r["full_name"], "link_status": r["status"],
                    "student_status": r["student_status"], "permissions": json.loads(r["permissions"]),
                    "consent_history": history})
    return out


def update_permissions(conn, parent: dict, student_id: int, permissions: list[str]) -> dict:
    _active_link(conn, parent, student_id)
    bad = set(permissions or []) - set(PARENT_PERMISSIONS)
    if bad:
        raise AccountError("Unknown permission requested.", 400, field="permissions")
    perms = sorted(set(permissions or []))
    conn.execute("UPDATE parent_student_links SET permissions=?, updated_at=? WHERE parent_user_id=? AND "
                 "student_user_id=?", (json.dumps(perms), now_iso(), parent["id"], student_id))
    _consent_record(conn, student_id, parent["id"], "updated", perms, {"is_parent_or_guardian": True, "is_adult": True})
    return {"student_id": student_id, "permissions": perms}


def withdraw_consent(conn, parent: dict, student_id: int) -> None:
    _active_link(conn, parent, student_id)
    conn.execute("UPDATE parent_student_links SET status='revoked', updated_at=? WHERE parent_user_id=? AND "
                 "student_user_id=?", (now_iso(), parent["id"], student_id))
    _consent_record(conn, student_id, parent["id"], "withdrawn", [], {"is_parent_or_guardian": True, "is_adult": True})
    others = conn.execute("SELECT COUNT(*) FROM parent_student_links WHERE student_user_id=? AND status='active'",
                          (student_id,)).fetchone()[0]
    if others == 0:
        core.set_status(conn, student_id, "suspended")
        core.revoke_all_sessions(conn, student_id)


# ---------------------------------------------------------------- pathway 3

def register_learner(conn, *, full_name, date_of_birth, email, password, accept_terms: bool) -> dict:
    name = clean_name(full_name)
    d = parse_dob(date_of_birth)
    if age_on(d) < 18:
        raise AccountError("Independent Learner accounts are for people aged 18 or over. Please use the "
                           "Individual Student option.", 400, field="date_of_birth", code="use_student")
    e = clean_email(email)
    check_password(password, email=e)
    if not accept_terms:
        raise AccountError("Please accept the terms and privacy notice to continue.", 400, field="accept_terms")
    uid = core.insert_user(conn, role="learner", full_name=name, password=password, status="pending_verification",
                           email=e, dob=d.isoformat())
    user = core.get_user(conn, uid)
    core.send_verification(conn, user)
    return {"token": core.create_session(conn, uid), "user": core.public_user(user)}


# ---------------------------------------------------------------- who am I / what next

def me(conn, user: dict) -> dict:
    out = {"user": core.public_user(user)}
    role, status = user["role"], user["status"]
    if status == "pending_verification":
        out["next_step"] = "verify_email"
    elif status == "pending_consent":
        out["next_step"] = "await_parent_consent"
        tok = conn.execute("SELECT email, expires_at FROM email_tokens WHERE purpose='parent_consent' AND user_id=? "
                           "AND used_at IS NULL ORDER BY id DESC LIMIT 1", (user["id"],)).fetchone()
        if tok:
            out["consent_request"] = {"sent_to": _mask(tok["email"]), "expires_at": tok["expires_at"]}
    elif status == "suspended":
        out["next_step"] = "suspended"
    elif role == "student":
        prof = row_to_dict(conn.execute("SELECT * FROM student_profiles WHERE user_id=?", (user["id"],)).fetchone())
        out["student"] = {"pathway": prof["pathway"], "onboarding_complete": bool(prof["onboarding_complete"])}
        enr = row_to_dict(conn.execute(
            "SELECT e.status, c.grade, c.division, c.academic_year, s.name AS school_name FROM class_enrollments e "
            "JOIN classes c ON c.id=e.class_id JOIN schools s ON s.id=c.school_id WHERE e.student_user_id=? "
            "ORDER BY e.id DESC LIMIT 1", (user["id"],)).fetchone())
        if enr:
            out["student"]["class"] = enr
        if enr and enr["status"] == "pending":
            out["next_step"] = "await_teacher_approval"
        elif enr and enr["status"] in ("rejected", "removed"):
            out["next_step"] = "enrollment_rejected"
        else:
            out["next_step"] = "dashboard" if prof["onboarding_complete"] else "onboarding"
    elif role == "learner":
        out["next_step"] = "onboarding"
    else:
        out["next_step"] = {"parent": "parent_home", "teacher": "teacher_home",
                            "school_admin": "admin_home", "platform_admin": "admin_home"}[role]
    return out


def _mask(email: str) -> str:
    name, _, domain = email.partition("@")
    return (name[:2] + "•" * max(1, len(name) - 2)) + "@" + domain
