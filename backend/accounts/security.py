"""Password hashing, tokens, codes and input validation.

Uses only Python's standard library (hashlib.scrypt, secrets, hmac), so it
needs no compiled add-ons.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from datetime import date

from .errors import AccountError

# scrypt parameters: ~16 MB memory, well above OWASP's minimum guidance.
_N, _R, _P, _DKLEN = 2 ** 14, 8, 1, 32
_MAXMEM = 64 * 1024 * 1024

# A short list of the most common passwords (blocked outright).
COMMON_PASSWORDS = {
    "password", "password1", "password123", "12345678", "123456789", "1234567890", "qwerty123",
    "qwertyuiop", "iloveyou", "11111111", "00000000", "abcd1234", "abc12345", "letmein1",
    "welcome1", "admin123", "india123", "sunshine", "football", "princess", "baseball",
    "dragon12", "monkey12", "superman", "asdfghjk", "passw0rd", "p@ssw0rd", "elevia123",
}

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
USERNAME_RE = re.compile(r"^[a-z0-9_.]{3,30}$")
CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"  # no 0/O, 1/I/L


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=_DKLEN, maxmem=_MAXMEM)
    b64 = lambda b: base64.b64encode(b).decode()
    return f"scrypt${_N}${_R}${_P}${b64(salt)}${b64(dk)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt_b64, dk_b64 = stored.split("$")
        if algo != "scrypt":
            return False
        salt, expected = base64.b64decode(salt_b64), base64.b64decode(dk_b64)
        dk = hashlib.scrypt(password.encode(), salt=salt, n=int(n), r=int(r), p=int(p),
                            dklen=len(expected), maxmem=_MAXMEM)
        return hmac.compare_digest(dk, expected)
    except (ValueError, TypeError):
        return False


# A real hash used to equalise timing when the user doesn't exist.
_DUMMY_HASH = hash_password("dummy-password-for-timing")


def burn_time(password: str) -> None:
    verify_password(password, _DUMMY_HASH)


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_referral_code() -> str:
    raw = "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))
    return f"ELV-{raw[:4]}-{raw[4:]}"


def normalize_code(code: str) -> str:
    c = re.sub(r"[^A-Za-z0-9]", "", code or "").upper()
    if c.startswith("ELV"):
        c = c[3:]
    return f"ELV-{c[:4]}-{c[4:]}" if len(c) == 8 else ""


# ---------------------------------------------------------------- validation

def clean_email(email: str | None, required: bool = True) -> str | None:
    e = (email or "").strip().lower()
    if not e:
        if required:
            raise AccountError("Please enter an email address.", 400, field="email")
        return None
    if len(e) > 254 or not EMAIL_RE.match(e):
        raise AccountError("Please enter a valid email address.", 400, field="email")
    return e


def clean_username(username: str) -> str:
    u = (username or "").strip().lower()
    if not USERNAME_RE.match(u):
        raise AccountError("Username: 3-30 characters, using letters, numbers, dots or underscores.", 400,
                           field="username")
    return u


def clean_name(name: str, field: str = "full_name") -> str:
    n = " ".join((name or "").split())
    if not 2 <= len(n) <= 80:
        raise AccountError("Please enter a name between 2 and 80 characters.", 400, field=field)
    return n


def check_password(password: str, *, username: str | None = None, email: str | None = None) -> None:
    p = password or ""
    if len(p) < 8:
        raise AccountError("Password must be at least 8 characters.", 400, field="password")
    if len(p) > 128:
        raise AccountError("Password must be at most 128 characters.", 400, field="password")
    low = p.lower()
    if low in COMMON_PASSWORDS:
        raise AccountError("That password is too common. Please choose another.", 400, field="password")
    if (username and low == username.lower()) or (email and low == email.split("@")[0].lower()):
        raise AccountError("Your password can't be the same as your username or email.", 400, field="password")


def parse_dob(value: str) -> date:
    try:
        d = date.fromisoformat((value or "").strip())
    except ValueError:
        raise AccountError("Please enter a valid date of birth.", 400, field="date_of_birth") from None
    if d > date.today():
        raise AccountError("Date of birth can't be in the future.", 400, field="date_of_birth")
    if age_on(d) > 110:
        raise AccountError("Please check the date of birth.", 400, field="date_of_birth")
    return d


def age_on(dob: date, today: date | None = None) -> int:
    t = today or date.today()
    return t.year - dob.year - ((t.month, t.day) < (dob.month, dob.day))
