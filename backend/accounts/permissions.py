"""The single place that decides who may see whose data.

Role alone never grants access to another person's records. Access needs a live
relationship: an active parent link with the matching permission, a teacher
assigned to the class where the student is approved, or an active share grant.
"""
from __future__ import annotations

import json
from typing import Optional

from ..db import now_iso
from .errors import AccountError

SCOPES = ("profile", "progress", "assessments", "gaps", "activity", "roster")
PARENT_SCOPE_PERMISSION = {"progress": "view_progress", "gaps": "view_progress",
                           "assessments": "view_assessments", "activity": "view_activity"}


def access_via(conn, actor: dict, subject_id: int, scope: str) -> Optional[str]:
    """Return how the actor may see `scope` of the subject's data, or None."""
    if scope not in SCOPES:
        raise ValueError(scope)
    if actor["status"] != "active":
        return None
    if actor["id"] == subject_id:
        return "self"
    subject = conn.execute("SELECT role, status FROM users WHERE id=?", (subject_id,)).fetchone()
    if subject is None or subject["status"] != "active":
        return None  # nobody else sees a pending or suspended account
    role = actor["role"]

    if role == "parent" and subject["role"] == "student":
        link = conn.execute("SELECT permissions FROM parent_student_links WHERE parent_user_id=? AND student_user_id=? "
                            "AND status='active'", (actor["id"], subject_id)).fetchone()
        if link:
            perms = set(json.loads(link["permissions"]))
            if scope == "profile" or PARENT_SCOPE_PERMISSION.get(scope) in perms:
                return "parent_link"

    if role == "teacher" and subject["role"] == "student" and scope != "roster":
        row = conn.execute(
            "SELECT 1 FROM class_enrollments e JOIN teacher_class_assignments a ON a.class_id=e.class_id "
            "JOIN classes c ON c.id=e.class_id JOIN schools s ON s.id=c.school_id "
            "WHERE e.student_user_id=? AND e.status='approved' AND a.teacher_user_id=? "
            "AND s.subscription_status='active' AND (s.subscription_ends IS NULL OR s.subscription_ends > ?)",
            (subject_id, actor["id"], now_iso())).fetchone()
        if row:
            return "teacher_class"

    if role == "school_admin" and subject["role"] == "student" and scope in ("profile", "roster"):
        row = conn.execute(
            "SELECT 1 FROM school_memberships a JOIN school_memberships s ON s.school_id=a.school_id "
            "WHERE a.user_id=? AND a.role_at_school='admin' AND a.status='active' "
            "AND s.user_id=? AND s.role_at_school='student' AND s.status='active'", (actor["id"], subject_id)).fetchone()
        if row:
            return "school_admin"

    if subject["role"] == "learner" and scope != "roster":
        g = conn.execute("SELECT scopes FROM share_grants WHERE owner_user_id=? AND grantee_user_id=? AND status='active' "
                         "AND (expires_at IS NULL OR expires_at > ?)", (subject_id, actor["id"], now_iso())).fetchone()
        if g and (scope == "profile" or scope in json.loads(g["scopes"])):
            return "share_grant"
    return None


def require(conn, actor: dict, subject_id: int, scope: str, log: bool = True) -> str:
    via = access_via(conn, actor, subject_id, scope)
    if via is None:
        raise AccountError("Not found.", 404)  # 404, not 403: don't confirm the person exists
    if log and via != "self":
        conn.execute("INSERT INTO access_log (viewer_user_id, subject_user_id, what, via, created_at) VALUES (?,?,?,?,?)",
                     (actor["id"], subject_id, scope, via, now_iso()))
    return via


def visible_scopes(conn, actor: dict, subject_id: int) -> list[str]:
    return [s for s in SCOPES if access_via(conn, actor, subject_id, s)]
