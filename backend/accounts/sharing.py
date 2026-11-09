"""Adult learner sharing: nothing is shared unless the learner grants it."""
from __future__ import annotations

import json
from datetime import timedelta
from typing import Optional

from ..db import now_iso, row_to_dict, rows_to_dicts
from . import core, emailer
from .errors import AccountError
from .security import clean_email

SHARE_SCOPES = {"progress": "Progress summary", "assessments": "Assessment history",
                "gaps": "Learning gaps", "activity": "Recent activity"}
GRANTEE_ROLES = ("parent", "teacher", "learner")


def _scopes(scopes) -> list[str]:
    s = sorted(set(scopes or []))
    if not s:
        raise AccountError("Choose at least one thing to share.", 400, field="scopes")
    if set(s) - set(SHARE_SCOPES):
        raise AccountError("Unknown sharing option.", 400, field="scopes")
    return s


def _require_learner(user: dict) -> None:
    if user["role"] != "learner" or user["status"] != "active":
        raise AccountError("Only active independent learner accounts can manage sharing.", 403)


def _expire_old(conn) -> None:
    conn.execute("UPDATE share_grants SET status='expired', updated_at=? WHERE status IN ('active','invited') "
                 "AND expires_at IS NOT NULL AND expires_at < ?", (now_iso(), now_iso()))


def _own_grant(conn, owner: dict, grant_id: int) -> dict:
    g = row_to_dict(conn.execute("SELECT * FROM share_grants WHERE id=? AND owner_user_id=?", (grant_id, owner["id"])).fetchone())
    if g is None:
        raise AccountError("Not found.", 404)
    return g


def invite(conn, owner: dict, email: str, scopes, expires_days: Optional[int] = None) -> dict:
    _require_learner(owner)
    e = clean_email(email)
    if e == owner["email"]:
        raise AccountError("You can't share with yourself.", 400, field="email")
    s = _scopes(scopes)
    exp = core.iso(core.utcnow() + timedelta(days=int(expires_days))) if expires_days else None
    if expires_days is not None and not 1 <= int(expires_days) <= 365:
        raise AccountError("Sharing can last 1 to 365 days.", 400)
    t = now_iso()
    cur = conn.execute("INSERT INTO share_grants (owner_user_id, invite_email, scopes, status, expires_at, created_at, "
                       "updated_at) VALUES (?,?,?,?,?,?,?)", (owner["id"], e, json.dumps(s), "invited", exp, t, t))
    raw = core.issue_token(conn, "share_invite", e, owner["id"], {"grant_id": cur.lastrowid})
    subj, body = emailer.share_invite(owner["full_name"], emailer.link("share", raw))
    emailer.send(conn, e, subj, body)
    return {"grant_id": cur.lastrowid, "status": "invited", "scopes": s, "expires_at": exp}


def accept_invite(conn, user: dict, raw: str) -> dict:
    tok = core.peek_token(conn, raw, "share_invite")
    if user["role"] not in GRANTEE_ROLES or user["status"] != "active":
        raise AccountError("Sign in with a parent, teacher or adult account to accept.", 403)
    if (user["email"] or "") != tok["email"]:
        raise AccountError("This invitation was sent to a different email address.", 403, code="wrong_account")
    g = row_to_dict(conn.execute("SELECT * FROM share_grants WHERE id=?", (tok["payload"]["grant_id"],)).fetchone())
    if g is None or g["status"] != "invited":
        raise AccountError("This invitation is no longer available.", 400, code="bad_token")
    conn.execute("UPDATE share_grants SET status='active', grantee_user_id=?, updated_at=? WHERE id=?",
                 (user["id"], now_iso(), g["id"]))
    core.consume_token(conn, tok["id"])
    owner = core.get_user(conn, g["owner_user_id"])
    return {"grant_id": g["id"], "owner_name": owner["full_name"], "scopes": json.loads(g["scopes"])}


def request_access(conn, requester: dict, learner_email: str) -> dict:
    """Generic reply either way, so it can't be used to discover who has an account."""
    if requester["role"] not in ("parent", "teacher") or requester["status"] != "active":
        raise AccountError("Only parent and teacher accounts can request access.", 403)
    e = clean_email(learner_email)
    key = f"share-request:{requester['id']}"
    if core.rate_limited(conn, key, 10, 60):
        raise AccountError("Please wait a while before sending more requests.", 429)
    core.record_event(conn, key)
    learner = row_to_dict(conn.execute("SELECT * FROM users WHERE email=? AND role='learner' AND status='active'",
                                       (e,)).fetchone())
    if learner:
        open_ = conn.execute("SELECT 1 FROM share_grants WHERE owner_user_id=? AND grantee_user_id=? AND status IN "
                             "('requested','active')", (learner["id"], requester["id"])).fetchone()
        if not open_:
            t = now_iso()
            conn.execute("INSERT INTO share_grants (owner_user_id, grantee_user_id, scopes, status, created_at, "
                         "updated_at) VALUES (?,?,?,?,?,?)", (learner["id"], requester["id"], "[]", "requested", t, t))
            subj, body = emailer.share_request(requester["full_name"], f"{emailer.app_base_url()}/?action=sharing")
            emailer.send(conn, e, subj, body)
    return {"message": "If that person has an ELEVIA learner account, they've been asked. Nothing is shared "
                       "unless they approve."}


def respond(conn, owner: dict, grant_id: int, approve: bool, scopes=None) -> dict:
    _require_learner(owner)
    g = _own_grant(conn, owner, grant_id)
    if g["status"] != "requested":
        raise AccountError("This request has already been answered.", 409)
    if approve:
        s = _scopes(scopes)
        conn.execute("UPDATE share_grants SET status='active', scopes=?, updated_at=? WHERE id=?",
                     (json.dumps(s), now_iso(), grant_id))
        return {"grant_id": grant_id, "status": "active", "scopes": s}
    conn.execute("UPDATE share_grants SET status='rejected', updated_at=? WHERE id=?", (now_iso(), grant_id))
    return {"grant_id": grant_id, "status": "rejected"}


def update_scopes(conn, owner: dict, grant_id: int, scopes) -> dict:
    _require_learner(owner)
    g = _own_grant(conn, owner, grant_id)
    if g["status"] not in ("active", "invited"):
        raise AccountError("Only current shares can be changed.", 409)
    s = _scopes(scopes)
    conn.execute("UPDATE share_grants SET scopes=?, updated_at=? WHERE id=?", (json.dumps(s), now_iso(), grant_id))
    return {"grant_id": grant_id, "scopes": s}


def revoke(conn, owner: dict, grant_id: int) -> dict:
    _require_learner(owner)
    g = _own_grant(conn, owner, grant_id)
    if g["status"] not in ("active", "invited", "requested"):
        raise AccountError("This share has already ended.", 409)
    conn.execute("UPDATE share_grants SET status='revoked', updated_at=? WHERE id=?", (now_iso(), grant_id))
    if g["status"] == "invited":
        core.invalidate_tokens(conn, "share_invite", email=g["invite_email"])
    return {"grant_id": grant_id, "status": "revoked"}


def list_mine(conn, owner: dict) -> dict:
    _require_learner(owner)
    _expire_old(conn)
    rows = rows_to_dicts(conn.execute(
        "SELECT g.*, u.full_name AS grantee_name, u.role AS grantee_role, u.email AS grantee_email FROM share_grants g "
        "LEFT JOIN users u ON u.id=g.grantee_user_id WHERE g.owner_user_id=? ORDER BY g.id DESC", (owner["id"],)).fetchall())
    for r in rows:
        r["scopes"] = json.loads(r["scopes"])
    views = rows_to_dicts(conn.execute(
        "SELECT a.what, a.created_at, u.full_name AS viewer FROM access_log a JOIN users u ON u.id=a.viewer_user_id "
        "WHERE a.subject_user_id=? AND a.viewer_user_id<>? ORDER BY a.id DESC LIMIT 50", (owner["id"], owner["id"])).fetchall())
    return {"shares": [r for r in rows if r["status"] != "requested"],
            "requests": [r for r in rows if r["status"] == "requested"], "access_log": views,
            "scope_labels": SHARE_SCOPES}


def shared_with_me(conn, user: dict) -> list[dict]:
    _expire_old(conn)
    rows = rows_to_dicts(conn.execute(
        "SELECT g.id, g.scopes, g.expires_at, u.id AS owner_id, u.full_name AS owner_name FROM share_grants g "
        "JOIN users u ON u.id=g.owner_user_id WHERE g.grantee_user_id=? AND g.status='active'", (user["id"],)).fetchall())
    for r in rows:
        r["scopes"] = json.loads(r["scopes"])
    return rows
