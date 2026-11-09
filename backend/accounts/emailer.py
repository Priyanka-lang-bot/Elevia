"""Outgoing email.

EMAIL_MODE=smtp sends through any SMTP service (Gmail app password, Brevo, Resend...).
EMAIL_MODE=outbox (the default) saves emails in the `email_outbox` table instead of
sending them, so flows can be tested without an email provider. Outbox mode is
clearly a development mode: nothing reaches a real inbox.
"""
from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

from ..db import now_iso

log = logging.getLogger("elevia.email")


def mode() -> str:
    m = os.getenv("EMAIL_MODE", "outbox").strip().lower()
    return m if m in ("smtp", "outbox") else "outbox"


def app_base_url() -> str:
    return os.getenv("APP_BASE_URL", "http://localhost:8501").rstrip("/")


def link(action: str, token: str) -> str:
    return f"{app_base_url()}/?action={action}&token={token}"


def send(conn, to: str, subject: str, body: str) -> None:
    """Send now (smtp) or store (outbox). Stored rows are written in the caller's transaction."""
    if mode() == "outbox":
        conn.execute("INSERT INTO email_outbox (to_email, subject, body, created_at) VALUES (?,?,?,?)",
                     (to, subject, body, now_iso()))
        log.info("Email saved to outbox (not sent): %s -> %s", subject, to)
        return
    msg = EmailMessage()
    msg["From"] = os.getenv("EMAIL_FROM", os.getenv("SMTP_USER", ""))
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    host, port = os.getenv("SMTP_HOST", ""), int(os.getenv("SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=15) as s:
        s.starttls(context=ssl.create_default_context())
        s.login(os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASSWORD", ""))
        s.send_message(msg)


SIGN_OFF = "\n\nIf you didn't expect this email, you can ignore it.\n— ELEVIA"


def parent_consent(child_first_name: str, parent_name: str, url: str) -> tuple[str, str]:
    return (f"{child_first_name} wants to use ELEVIA: your consent is needed",
            f"Hello {parent_name},\n\n{child_first_name} has started creating an ELEVIA account, a learning "
            f"platform that helps students find and close gaps in what they've learned.\n\n"
            f"Because {child_first_name} is under 18, the account stays locked until you review what ELEVIA "
            f"collects and decide whether to give consent. You'll also get your own parent account.\n\n"
            f"Review and decide (link valid for 72 hours):\n{url}" + SIGN_OFF)


def verify_email(name: str, url: str) -> tuple[str, str]:
    return ("Confirm your email for ELEVIA",
            f"Hello {name},\n\nPlease confirm your email address to activate your ELEVIA account "
            f"(link valid for 48 hours):\n{url}" + SIGN_OFF)


def reset_password(name: str, url: str) -> tuple[str, str]:
    return ("Reset your ELEVIA password",
            f"Hello {name},\n\nUse this link to choose a new password (valid for 1 hour):\n{url}" + SIGN_OFF)


def staff_invite(role_label: str, school_name: str, url: str) -> tuple[str, str]:
    return (f"You're invited to ELEVIA as {role_label} at {school_name}",
            f"Hello,\n\nYou've been invited to join {school_name} on ELEVIA as {role_label}.\n\n"
            f"Set up your account (link valid for 7 days):\n{url}" + SIGN_OFF)


def share_invite(owner_name: str, url: str) -> tuple[str, str]:
    return (f"{owner_name} wants to share their ELEVIA progress with you",
            f"Hello,\n\n{owner_name} has invited you to view parts of their learning progress on ELEVIA. "
            f"They choose what you can see and can stop sharing at any time.\n\nAccept the invitation "
            f"(valid for 7 days):\n{url}" + SIGN_OFF)


def share_request(requester_name: str, url: str) -> tuple[str, str]:
    return (f"{requester_name} asked to see your ELEVIA progress",
            f"Hello,\n\n{requester_name} has asked to view your learning progress on ELEVIA. Nothing is "
            f"shared unless you approve. Review the request in your sharing settings:\n{url}" + SIGN_OFF)
