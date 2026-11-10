"""HTTP routes for accounts, consent, schools and sharing.

Every route runs in one database transaction. Sessions come from the
`Authorization: Bearer <token>` header.
"""
from __future__ import annotations

import os
from typing import Callable, Optional

from fastapi import APIRouter, Depends, Header, Request, Response
from pydantic import BaseModel, Field

from .. import db
from . import core, emailer, pathways, permissions, schools, sharing
from .errors import AccountError

router = APIRouter()
COOKIE = "elevia_session"
WEB_HEADER = "x-elevia-web"  # sent by ELEVIA's own web page; a cross-site form can't add it


def _tx(fn: Callable):
    bucket = [] if emailer.demo_links_enabled() else None
    token = emailer.demo_emails.set(bucket)
    try:
        with db.transaction() as conn:
            result = fn(conn)
    finally:
        emailer.demo_emails.reset(token)
    if bucket and isinstance(result, dict):
        result = {**result, "demo_emails": bucket}  # DEMO MODE ONLY: shows links instead of sending
    return result


def _with_session(request: Request, response: Response, result: dict) -> dict:
    """Put the session in an HttpOnly cookie. ELEVIA's web page never sees the token itself."""
    tok = result.get("token") if isinstance(result, dict) else None
    if tok:
        https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
        response.set_cookie(COOKIE, tok, max_age=core.SESSION_DAYS * 86400, httponly=True, secure=https,
                            samesite="lax", path="/")
        if request.headers.get(WEB_HEADER) == "1":
            result = {k: v for k, v in result.items() if k != "token"}
    return result


def _bearer(request: Request, authorization: str = Header(default="")) -> str:
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    tok = request.cookies.get(COOKIE, "")
    if tok and request.method not in ("GET", "HEAD") and request.headers.get(WEB_HEADER) != "1":
        raise AccountError("Request blocked.", 403, code="csrf")  # cookie sent by another site
    return tok


def current_user(token: str = Depends(_bearer)) -> dict:
    with db.transaction() as conn:
        user = core.user_for_session(conn, token)
    if user is None:
        raise AccountError("Please log in.", 401, code="not_logged_in")
    return user


def optional_user(token: str = Depends(_bearer)) -> Optional[dict]:
    if not token:
        return None
    with db.transaction() as conn:
        return core.user_for_session(conn, token)


def active_user(user: dict = Depends(current_user)) -> dict:
    if user["status"] != "active":
        raise AccountError("Your account isn't active yet.", 403, code="not_active")
    return user


# ---------------------------------------------------------------- bodies

class Login(BaseModel):
    identifier: str = Field(max_length=254)
    password: str = Field(max_length=128)


class TokenBody(BaseModel):
    token: str = Field(min_length=10, max_length=200)


class EmailBody(BaseModel):
    email: str = Field(max_length=254)


class ResetBody(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    new_password: str = Field(max_length=128)


class StudentSignup(BaseModel):
    full_name: str = Field(max_length=80)
    date_of_birth: str = Field(max_length=10)
    username: str = Field(max_length=30)
    password: str = Field(max_length=128)
    student_email: Optional[str] = Field(default=None, max_length=254)
    parent_name: Optional[str] = Field(default=None, max_length=80)
    parent_email: Optional[str] = Field(default=None, max_length=254)


class SchoolStudentSignup(StudentSignup):
    code: str = Field(max_length=20)


class LearnerSignup(BaseModel):
    full_name: str = Field(max_length=80)
    date_of_birth: str = Field(max_length=10)
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)
    accept_terms: bool = False


class CodeBody(BaseModel):
    code: str = Field(max_length=20)


class ConsentAccept(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    is_parent_or_guardian: bool = False
    is_adult: bool = False
    agree_purposes: bool = False
    permissions: list[str] = []
    full_name: Optional[str] = Field(default=None, max_length=80)
    password: Optional[str] = Field(default=None, max_length=128)


class ParentInviteResend(BaseModel):
    parent_name: Optional[str] = Field(default=None, max_length=80)
    parent_email: Optional[str] = Field(default=None, max_length=254)


class Permissions(BaseModel):
    permissions: list[str] = []


class StaffAccept(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    full_name: str = Field(max_length=80)
    password: str = Field(max_length=128)


class NewClass(BaseModel):
    grade: int
    division: str = Field(max_length=10)
    academic_year: str = Field(max_length=9)


class Assignment(BaseModel):
    teacher_id: int
    class_id: int
    subject: str = Field(default="", max_length=40)
    can_create_codes: Optional[bool] = None


class NewCode(BaseModel):
    class_id: int
    expires_days: int = 30
    max_uses: int = 60


class ShareInvite(BaseModel):
    email: str = Field(max_length=254)
    scopes: list[str]
    expires_days: Optional[int] = None


class ShareRequest(BaseModel):
    learner_email: str = Field(max_length=254)


class ShareRespond(BaseModel):
    approve: bool
    scopes: list[str] = []


class Scopes(BaseModel):
    scopes: list[str]


# ---------------------------------------------------------------- auth

@router.post("/auth/login")
def login(body: Login, request: Request, response: Response):
    return _with_session(request, response, _tx(lambda c: core.login(c, body.identifier, body.password)))


@router.post("/auth/logout")
def logout(response: Response, token: str = Depends(_bearer)):
    _tx(lambda c: core.revoke_session(c, token))
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.get("/auth/me")
def me(user: dict = Depends(current_user)):
    return _tx(lambda c: pathways.me(c, user))


@router.post("/auth/verify-email")
def verify_email(body: TokenBody):
    return _tx(lambda c: core.verify_email(c, body.token))


@router.post("/auth/resend-verification")
def resend_verification(user: dict = Depends(current_user)):
    _tx(lambda c: core.resend_verification(c, user))
    return {"ok": True}


@router.post("/auth/forgot-password")
def forgot(body: EmailBody):
    _tx(lambda c: core.forgot_password(c, body.email))
    return {"message": "If an account uses that email, we've sent a reset link."}


@router.post("/auth/reset-password")
def reset(body: ResetBody):
    _tx(lambda c: core.reset_password(c, body.token, body.new_password))
    return {"message": "Password changed. Please log in."}


@router.post("/auth/register/student", status_code=201)
def register_student(body: StudentSignup, request: Request, response: Response):
    return _with_session(request, response, _tx(lambda c: pathways.register_individual_student(c, **body.model_dump())))


@router.post("/auth/register/school-student", status_code=201)
def register_school_student(body: SchoolStudentSignup, request: Request, response: Response,
                            x_client_id: str = Header(default="")):
    return _with_session(request, response, _tx(
        lambda c: schools.register_school_student(c, client_id=x_client_id, **body.model_dump())))


@router.post("/auth/register/learner", status_code=201)
def register_learner(body: LearnerSignup, request: Request, response: Response):
    return _with_session(request, response, _tx(lambda c: pathways.register_learner(c, **body.model_dump())))


@router.post("/auth/school-code/validate")
def validate_code(body: CodeBody, x_client_id: str = Header(default="")):
    return _tx(lambda c: schools.validate_code(c, body.code, x_client_id))


# ---------------------------------------------------------------- parent consent

@router.post("/consent/info")
def consent_info(body: TokenBody):
    return _tx(lambda c: pathways.consent_info(c, body.token))


@router.post("/consent/accept")
def consent_accept(body: ConsentAccept, request: Request, response: Response,
                   actor: Optional[dict] = Depends(optional_user)):
    d = body.model_dump()
    tok = d.pop("token")
    return _with_session(request, response, _tx(lambda c: pathways.accept_consent(c, tok, actor=actor, **d)))


@router.post("/consent/decline")
def consent_decline(body: TokenBody):
    _tx(lambda c: pathways.decline_consent(c, body.token))
    return {"message": "Thanks. The account request has been deleted."}


@router.post("/auth/resend-parent-invite")
def resend_parent(body: ParentInviteResend, user: dict = Depends(current_user)):
    _tx(lambda c: pathways.resend_parent_invite(c, user, body.parent_name, body.parent_email))
    return {"ok": True}


@router.get("/parent/children")
def children(user: dict = Depends(active_user)):
    return _tx(lambda c: pathways.list_children(c, user))


@router.put("/parent/children/{student_id}/permissions")
def child_permissions(student_id: int, body: Permissions, user: dict = Depends(active_user)):
    return _tx(lambda c: pathways.update_permissions(c, user, student_id, body.permissions))


@router.post("/parent/children/{student_id}/withdraw-consent")
def withdraw(student_id: int, user: dict = Depends(active_user)):
    _tx(lambda c: pathways.withdraw_consent(c, user, student_id))
    return {"ok": True}


# ---------------------------------------------------------------- staff invitations and schools

@router.post("/invites/info")
def invite_info(body: TokenBody):
    return _tx(lambda c: schools.invite_info(c, body.token))


@router.post("/invites/accept", status_code=201)
def invite_accept(body: StaffAccept, request: Request, response: Response):
    return _with_session(request, response, _tx(
        lambda c: schools.accept_staff_invite(c, body.token, full_name=body.full_name, password=body.password)))


@router.post("/school/classes", status_code=201)
def new_class(body: NewClass, user: dict = Depends(active_user)):
    return _tx(lambda c: schools.create_class(c, user, body.grade, body.division, body.academic_year))


@router.get("/school/classes")
def classes(user: dict = Depends(active_user)):
    return _tx(lambda c: schools.list_classes(c, user))


@router.post("/school/teachers/invite")
def invite_teacher(body: EmailBody, user: dict = Depends(active_user)):
    return _tx(lambda c: schools.invite_teacher(c, user, body.email))


@router.get("/school/teachers")
def teachers(user: dict = Depends(active_user)):
    return _tx(lambda c: schools.list_teachers(c, user))


@router.post("/school/assignments")
def assign(body: Assignment, user: dict = Depends(active_user)):
    return _tx(lambda c: schools.assign_teacher(c, user, body.teacher_id, body.class_id, body.subject,
                                                body.can_create_codes))


@router.post("/school/assignments/remove")
def unassign(body: Assignment, user: dict = Depends(active_user)):
    return _tx(lambda c: schools.unassign_teacher(c, user, body.teacher_id, body.class_id))


@router.post("/school/codes", status_code=201)
def new_code(body: NewCode, user: dict = Depends(active_user)):
    return _tx(lambda c: schools.create_code(c, user, body.class_id, body.expires_days, body.max_uses))


@router.get("/school/codes")
def codes(user: dict = Depends(active_user)):
    return _tx(lambda c: schools.list_codes(c, user))


@router.post("/school/codes/{code_id}/revoke")
def revoke_code(code_id: int, user: dict = Depends(active_user)):
    return _tx(lambda c: schools.revoke_code(c, user, code_id))


@router.get("/school/classes/{class_id}/roster")
def roster(class_id: int, user: dict = Depends(active_user)):
    return _tx(lambda c: schools.class_roster(c, user, class_id))


@router.post("/school/enrollments/{enrollment_id}/approve")
def approve(enrollment_id: int, user: dict = Depends(active_user)):
    return _tx(lambda c: schools.decide_enrollment(c, user, enrollment_id, True))


@router.post("/school/enrollments/{enrollment_id}/reject")
def reject(enrollment_id: int, user: dict = Depends(active_user)):
    return _tx(lambda c: schools.decide_enrollment(c, user, enrollment_id, False))


# ---------------------------------------------------------------- sharing

@router.get("/sharing")
def my_shares(user: dict = Depends(active_user)):
    return _tx(lambda c: sharing.list_mine(c, user))


@router.get("/sharing/with-me")
def with_me(user: dict = Depends(active_user)):
    return _tx(lambda c: sharing.shared_with_me(c, user))


@router.post("/sharing/invite", status_code=201)
def share_invite(body: ShareInvite, user: dict = Depends(active_user)):
    return _tx(lambda c: sharing.invite(c, user, body.email, body.scopes, body.expires_days))


@router.post("/sharing/accept")
def share_accept(body: TokenBody, user: dict = Depends(active_user)):
    return _tx(lambda c: sharing.accept_invite(c, user, body.token))


@router.post("/sharing/request")
def share_request(body: ShareRequest, user: dict = Depends(active_user)):
    return _tx(lambda c: sharing.request_access(c, user, body.learner_email))


@router.post("/sharing/{grant_id}/respond")
def share_respond(grant_id: int, body: ShareRespond, user: dict = Depends(active_user)):
    return _tx(lambda c: sharing.respond(c, user, grant_id, body.approve, body.scopes))


@router.put("/sharing/{grant_id}/scopes")
def share_scopes(grant_id: int, body: Scopes, user: dict = Depends(active_user)):
    return _tx(lambda c: sharing.update_scopes(c, user, grant_id, body.scopes))


@router.post("/sharing/{grant_id}/revoke")
def share_revoke(grant_id: int, user: dict = Depends(active_user)):
    return _tx(lambda c: sharing.revoke(c, user, grant_id))


# ---------------------------------------------------------------- access-checked view of another person

@router.get("/people/{user_id}/summary")
def person_summary(user_id: int, user: dict = Depends(active_user)):
    """What this viewer may see about a person. Learning data plugs in here in the learning phase."""
    def run(c):
        via = permissions.require(c, user, user_id, "profile")
        person = core.get_user(c, user_id)
        return {"id": person["id"], "full_name": person["full_name"], "role": person["role"], "access_via": via,
                "visible_scopes": permissions.visible_scopes(c, user, user_id)}
    return _tx(run)


# ---------------------------------------------------------------- development outbox

@router.get("/dev/outbox")
def outbox(limit: int = 20):
    """Only when ELEVIA_DEV_OUTBOX=1: shows saved emails (with their links) for local testing."""
    if os.getenv("ELEVIA_DEV_OUTBOX", "") != "1":
        raise AccountError("Not found.", 404)
    return _tx(lambda c: [dict(r) for r in c.execute(
        "SELECT id, to_email, subject, body, created_at FROM email_outbox ORDER BY id DESC LIMIT ?",
        (max(1, min(limit, 100)),)).fetchall()])
