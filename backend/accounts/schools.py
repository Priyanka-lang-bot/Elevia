"""Pathway 2: schools, staff invitations, classes, referral codes, enrolments."""
from __future__ import annotations

import json
from datetime import timedelta
from typing import Optional

from ..db import now_iso, row_to_dict, rows_to_dicts
from . import core, emailer
from .errors import AccountError
from .pathways import send_parent_invite, validate_parent_contact, validate_student_basics, purge_unconsented
from .security import check_password, clean_email, clean_name, new_referral_code, normalize_code

CODE_CHECKS_PER_CLIENT, CODE_WINDOW_MIN = 5, 15
GLOBAL_CODE_FAILS = 200
BAD_CODE = "That code isn't valid. Check it with your teacher."


# ---------------------------------------------------------------- platform admin (CLI)

def create_school(conn, *, name: str, admin_email: str, state: str = "", district: str = "",
                  udise_code: Optional[str] = None, subscription_days: int = 365, is_demo: bool = False) -> dict:
    """Used by the ELEVIA team (scripts/create_school.py). Returns the admin invitation link."""
    n = clean_name(name, field="name")
    email = clean_email(admin_email)
    ends = core.iso(core.utcnow() + timedelta(days=subscription_days))
    cur = conn.execute(
        "INSERT INTO schools (name, udise_code, state, district, source, verified, subscription_status, "
        "subscription_ends, is_demo, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (n, udise_code or None, state or None, district or None, "elevia_team", 1, "active", ends, int(is_demo),
         now_iso()))
    school_id = cur.lastrowid
    url = invite_staff(conn, school_id, email, "admin_invite")
    return {"school_id": school_id, "invite_url": url}


def invite_staff(conn, school_id: int, email: str, purpose: str) -> str:
    school = _school(conn, school_id)
    core.invalidate_tokens(conn, purpose, email=email)
    raw = core.issue_token(conn, purpose, email, None, {"school_id": school_id})
    url = emailer.link("invite", raw)
    label = "school admin" if purpose == "admin_invite" else "a teacher"
    subj, body = emailer.staff_invite(label, school["name"], url)
    emailer.send(conn, email, subj, body)
    return url


def invite_info(conn, raw: str) -> dict:
    for purpose in ("teacher_invite", "admin_invite"):
        try:
            tok = core.peek_token(conn, raw, purpose)
        except AccountError:
            continue
        school = _school(conn, tok["payload"]["school_id"])
        return {"role": "teacher" if purpose == "teacher_invite" else "school_admin", "email": tok["email"],
                "school_name": school["name"], "account_exists": core.email_taken(conn, tok["email"])}
    raise AccountError("This link is invalid or has expired. Please ask for a new one.", 400, code="bad_token")


def accept_staff_invite(conn, raw: str, *, full_name: str, password: str) -> dict:
    tok, purpose = None, None
    for p in ("teacher_invite", "admin_invite"):
        try:
            tok, purpose = core.peek_token(conn, raw, p), p
            break
        except AccountError:
            continue
    if tok is None:
        raise AccountError("This link is invalid or has expired. Please ask for a new one.", 400, code="bad_token")
    school_id = tok["payload"]["school_id"]
    name = clean_name(full_name)
    check_password(password, email=tok["email"])
    role = "teacher" if purpose == "teacher_invite" else "school_admin"
    uid = core.insert_user(conn, role=role, full_name=name, password=password, status="active", email=tok["email"],
                           email_verified=True)
    conn.execute("INSERT INTO school_memberships (user_id, school_id, role_at_school, status, created_at) "
                 "VALUES (?,?,?,?,?)", (uid, school_id, "teacher" if role == "teacher" else "admin", "active", now_iso()))
    if role == "teacher":
        conn.execute("INSERT INTO teacher_profiles (user_id, school_id) VALUES (?,?)", (uid, school_id))
    core.consume_token(conn, tok["id"])
    return {"token": core.create_session(conn, uid), "user": core.public_user(core.get_user(conn, uid))}


# ---------------------------------------------------------------- helpers

def _school(conn, school_id: int) -> dict:
    s = row_to_dict(conn.execute("SELECT * FROM schools WHERE id=?", (school_id,)).fetchone())
    if s is None:
        raise AccountError("School not found.", 404)
    return s


def subscription_active(school: dict) -> bool:
    return school["subscription_status"] == "active" and (not school["subscription_ends"]
                                                          or school["subscription_ends"] > now_iso())


def staff_school(conn, user: dict, *, admin_only: bool = False) -> dict:
    """The school a teacher/admin belongs to; raises if not staff."""
    allowed = ("school_admin",) if admin_only else ("school_admin", "teacher")
    if user["role"] not in allowed:
        raise AccountError("You don't have access to this.", 403)
    m = conn.execute("SELECT school_id FROM school_memberships WHERE user_id=? AND status='active' AND "
                     "role_at_school IN ('teacher','admin')", (user["id"],)).fetchone()
    if m is None:
        raise AccountError("You don't have access to this.", 403)
    return _school(conn, m["school_id"])


def _class_in_school(conn, class_id: int, school_id: int) -> dict:
    c = row_to_dict(conn.execute("SELECT * FROM classes WHERE id=? AND school_id=?", (class_id, school_id)).fetchone())
    if c is None:
        raise AccountError("Class not found.", 404)
    return c


def class_label(c: dict) -> str:
    return f"Class {c['grade']} {c['division']}, {c['academic_year']}"


def teacher_has_class(conn, teacher_id: int, class_id: int) -> bool:
    return conn.execute("SELECT 1 FROM teacher_class_assignments WHERE teacher_user_id=? AND class_id=?",
                        (teacher_id, class_id)).fetchone() is not None


# ---------------------------------------------------------------- school admin

def create_class(conn, admin: dict, grade: int, division: str, academic_year: str) -> dict:
    school = staff_school(conn, admin, admin_only=True)
    div = (division or "").strip().upper()
    if not 1 <= int(grade) <= 12 or not 1 <= len(div) <= 10 or not 4 <= len((academic_year or "").strip()) <= 9:
        raise AccountError("Enter a grade from 1 to 12, a division and an academic year (e.g. 2026-27).", 400)
    try:
        cur = conn.execute("INSERT INTO classes (school_id, grade, division, academic_year, created_at) VALUES (?,?,?,?,?)",
                           (school["id"], int(grade), div, academic_year.strip(), now_iso()))
    except Exception:
        raise AccountError("That class already exists.", 409) from None
    return row_to_dict(conn.execute("SELECT * FROM classes WHERE id=?", (cur.lastrowid,)).fetchone())


def list_classes(conn, user: dict) -> list[dict]:
    school = staff_school(conn, user)
    if user["role"] == "teacher":
        rows = conn.execute("SELECT DISTINCT c.* FROM classes c JOIN teacher_class_assignments t ON t.class_id=c.id "
                            "WHERE t.teacher_user_id=? ORDER BY grade, division", (user["id"],)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM classes WHERE school_id=? ORDER BY grade, division", (school["id"],)).fetchall()
    out = []
    for c in rows_to_dicts(rows):
        counts = {r["status"]: r["n"] for r in conn.execute(
            "SELECT status, COUNT(*) n FROM class_enrollments WHERE class_id=? GROUP BY status", (c["id"],)).fetchall()}
        out.append({**c, "label": class_label(c), "approved": counts.get("approved", 0), "pending": counts.get("pending", 0)})
    return out


def invite_teacher(conn, admin: dict, email: str) -> dict:
    school = staff_school(conn, admin, admin_only=True)
    e = clean_email(email)
    if core.email_taken(conn, e):
        raise AccountError("An account with this email already exists.", 409, field="email")
    invite_staff(conn, school["id"], e, "teacher_invite")
    return {"invited": e}


def list_teachers(conn, admin: dict) -> dict:
    school = staff_school(conn, admin, admin_only=True)
    teachers = rows_to_dicts(conn.execute(
        "SELECT u.id, u.full_name, u.email, p.can_create_codes FROM users u JOIN teacher_profiles p ON p.user_id=u.id "
        "WHERE p.school_id=? ORDER BY u.full_name", (school["id"],)).fetchall())
    for t in teachers:
        t["classes"] = [class_label(c) for c in rows_to_dicts(conn.execute(
            "SELECT c.* FROM classes c JOIN teacher_class_assignments a ON a.class_id=c.id WHERE a.teacher_user_id=?",
            (t["id"],)).fetchall())]
        t["can_create_codes"] = bool(t["can_create_codes"])
    pending = [r["email"] for r in conn.execute(
        "SELECT email FROM email_tokens WHERE purpose='teacher_invite' AND used_at IS NULL AND expires_at>? AND "
        "json_extract(payload,'$.school_id')=?", (now_iso(), school["id"])).fetchall()]
    return {"teachers": teachers, "pending_invites": pending}


def assign_teacher(conn, admin: dict, teacher_id: int, class_id: int, subject: str = "",
                   can_create_codes: Optional[bool] = None) -> dict:
    school = staff_school(conn, admin, admin_only=True)
    _class_in_school(conn, class_id, school["id"])
    t = conn.execute("SELECT 1 FROM teacher_profiles WHERE user_id=? AND school_id=?", (teacher_id, school["id"])).fetchone()
    if t is None:
        raise AccountError("Teacher not found at your school.", 404)
    conn.execute("INSERT OR IGNORE INTO teacher_class_assignments (teacher_user_id, class_id, subject, created_at) "
                 "VALUES (?,?,?,?)", (teacher_id, class_id, (subject or "").strip()[:40], now_iso()))
    if can_create_codes is not None:
        conn.execute("UPDATE teacher_profiles SET can_create_codes=? WHERE user_id=?", (int(can_create_codes), teacher_id))
    return {"ok": True}


def unassign_teacher(conn, admin: dict, teacher_id: int, class_id: int) -> dict:
    school = staff_school(conn, admin, admin_only=True)
    _class_in_school(conn, class_id, school["id"])
    conn.execute("DELETE FROM teacher_class_assignments WHERE teacher_user_id=? AND class_id=?", (teacher_id, class_id))
    return {"ok": True}


# ---------------------------------------------------------------- referral codes

def create_code(conn, user: dict, class_id: int, expires_days: int = 30, max_uses: int = 60) -> dict:
    school = staff_school(conn, user)
    if not subscription_active(school):
        raise AccountError("Your school's ELEVIA subscription isn't active, so new codes can't be created.", 403)
    c = _class_in_school(conn, class_id, school["id"])
    if user["role"] == "teacher":
        prof = conn.execute("SELECT can_create_codes FROM teacher_profiles WHERE user_id=?", (user["id"],)).fetchone()
        if not (prof and prof["can_create_codes"] and teacher_has_class(conn, user["id"], class_id)):
            raise AccountError("You can't create codes for this class. Ask your school admin.", 403)
    if not 1 <= int(expires_days) <= 180 or not 1 <= int(max_uses) <= 500:
        raise AccountError("Expiry must be 1-180 days and uses 1-500.", 400)
    for _ in range(5):
        code = new_referral_code()
        if conn.execute("SELECT 1 FROM referral_codes WHERE code=?", (code,)).fetchone() is None:
            break
    exp = core.iso(core.utcnow() + timedelta(days=int(expires_days)))
    conn.execute("INSERT INTO referral_codes (code, school_id, class_id, created_by, expires_at, max_uses, status, "
                 "created_at) VALUES (?,?,?,?,?,?,?,?)", (code, school["id"], class_id, user["id"], exp, int(max_uses),
                                                          "active", now_iso()))
    return {"code": code, "class": class_label(c), "expires_at": exp, "max_uses": int(max_uses)}


def list_codes(conn, user: dict) -> list[dict]:
    school = staff_school(conn, user)
    rows = rows_to_dicts(conn.execute(
        "SELECT r.*, c.grade, c.division, c.academic_year FROM referral_codes r JOIN classes c ON c.id=r.class_id "
        "WHERE r.school_id=? ORDER BY r.id DESC", (school["id"],)).fetchall())
    if user["role"] == "teacher":
        rows = [r for r in rows if teacher_has_class(conn, user["id"], r["class_id"])]
    for r in rows:
        r["label"] = class_label(r)
        r["usable"] = r["status"] == "active" and r["expires_at"] > now_iso() and r["uses"] < r["max_uses"]
    return rows


def revoke_code(conn, user: dict, code_id: int) -> dict:
    school = staff_school(conn, user)
    r = row_to_dict(conn.execute("SELECT * FROM referral_codes WHERE id=? AND school_id=?", (code_id, school["id"])).fetchone())
    if r is None or (user["role"] == "teacher" and not teacher_has_class(conn, user["id"], r["class_id"])):
        raise AccountError("Code not found.", 404)
    conn.execute("UPDATE referral_codes SET status='revoked' WHERE id=?", (code_id,))
    return {"ok": True}


def _lookup_code(conn, code: str) -> Optional[dict]:
    norm = normalize_code(code)
    if not norm:
        return None
    r = row_to_dict(conn.execute(
        "SELECT r.*, s.name AS school_name, s.subscription_status, s.subscription_ends, s.consent_handled_by_school, "
        "c.grade, c.division, c.academic_year FROM referral_codes r JOIN schools s ON s.id=r.school_id "
        "JOIN classes c ON c.id=r.class_id WHERE r.code=?", (norm,)).fetchone())
    if (r is None or r["status"] != "active" or r["expires_at"] < now_iso() or r["uses"] >= r["max_uses"]
            or not subscription_active({"subscription_status": r["subscription_status"],
                                        "subscription_ends": r["subscription_ends"]})):
        return None
    return r


def validate_code(conn, code: str, client_id: str) -> dict:
    ckey, gkey = f"code:{(client_id or 'anon')[:64]}", "code:global"
    if core.rate_limited(conn, ckey, CODE_CHECKS_PER_CLIENT, CODE_WINDOW_MIN) or \
            core.rate_limited(conn, gkey, GLOBAL_CODE_FAILS, CODE_WINDOW_MIN):
        raise AccountError("Too many attempts. Please wait 15 minutes and try again.", 429, code="locked")
    r = _lookup_code(conn, code)
    if r is None:
        core.record_event(conn, ckey)
        core.record_event(conn, gkey)
        raise AccountError(BAD_CODE, 400, field="code", code="bad_code")
    return {"school_name": r["school_name"], "class_label": class_label(r)}


def register_school_student(conn, *, code, full_name, date_of_birth, username, password, student_email=None,
                            parent_name=None, parent_email=None, client_id: str = "") -> dict:
    validate_code(conn, code, client_id)  # rate limit + friendly error (before any write)
    purge_unconsented(conn)
    r = _lookup_code(conn, code)
    name, d, age, uname, email = validate_student_basics(full_name, date_of_birth, username, password, student_email)
    needs_consent = age < 18 and not r["consent_handled_by_school"]
    if needs_consent:
        pname, pemail = validate_parent_contact(parent_name, parent_email, email)
    upd = conn.execute("UPDATE referral_codes SET uses=uses+1 WHERE id=? AND uses<max_uses AND status='active'",
                       (r["id"],))
    if upd.rowcount == 0:
        raise AccountError(BAD_CODE, 400, field="code", code="bad_code")
    uid = core.insert_user(conn, role="student", full_name=name, password=password,
                           status="pending_consent" if needs_consent else "active", email=email, username=uname,
                           dob=d.isoformat())
    conn.execute("INSERT INTO student_profiles (user_id, pathway, grade, division, school_id) VALUES (?,?,?,?,?)",
                 (uid, "school", r["grade"], r["division"], r["school_id"]))
    conn.execute("INSERT INTO school_memberships (user_id, school_id, role_at_school, status, created_at) "
                 "VALUES (?,?,?,?,?)", (uid, r["school_id"], "student", "active", now_iso()))
    conn.execute("INSERT INTO class_enrollments (student_user_id, class_id, status, via_code_id, created_at) "
                 "VALUES (?,?,?,?,?)", (uid, r["class_id"], "pending", r["id"], now_iso()))
    if needs_consent:
        send_parent_invite(conn, uid, name, pname, pemail)
    return {"token": core.create_session(conn, uid), "user": core.public_user(core.get_user(conn, uid)),
            "school_name": r["school_name"], "class_label": class_label(r)}


# ---------------------------------------------------------------- teacher

def class_roster(conn, teacher: dict, class_id: int) -> dict:
    school = staff_school(conn, teacher)
    c = _class_in_school(conn, class_id, school["id"])
    if teacher["role"] == "teacher" and not teacher_has_class(conn, teacher["id"], class_id):
        raise AccountError("Class not found.", 404)
    rows = rows_to_dicts(conn.execute(
        "SELECT e.id AS enrollment_id, e.status, e.created_at, u.id AS student_id, u.full_name, u.status AS account_status "
        "FROM class_enrollments e JOIN users u ON u.id=e.student_user_id WHERE e.class_id=? AND e.status IN "
        "('pending','approved') ORDER BY e.status DESC, u.full_name", (class_id,)).fetchall())
    return {"class": {**c, "label": class_label(c)}, "students": rows}


def decide_enrollment(conn, teacher: dict, enrollment_id: int, approve: bool) -> dict:
    if teacher["role"] != "teacher":
        raise AccountError("Only the class teacher can approve students.", 403)
    e = row_to_dict(conn.execute("SELECT * FROM class_enrollments WHERE id=?", (enrollment_id,)).fetchone())
    if e is None or not teacher_has_class(conn, teacher["id"], e["class_id"]):
        raise AccountError("Not found.", 404)
    if e["status"] != "pending":
        raise AccountError("This request has already been decided.", 409)
    conn.execute("UPDATE class_enrollments SET status=?, decided_by=?, decided_at=? WHERE id=?",
                 ("approved" if approve else "rejected", teacher["id"], now_iso(), enrollment_id))
    return {"enrollment_id": enrollment_id, "status": "approved" if approve else "rejected"}
