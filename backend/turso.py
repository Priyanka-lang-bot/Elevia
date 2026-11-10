"""Minimal Turso (libSQL) connection over its HTTP API, shaped like sqlite3.

Used automatically when TURSO_DATABASE_URL is set (e.g. on Vercel, where the local
disk is temporary). The rest of ELEVIA keeps calling conn.execute(...) exactly as
with sqlite3. Pure Python (httpx), no compiled packages.

Protocol: POST <db>/v2/pipeline with {"baton", "requests":[{"type":"execute","stmt":...}]}.
A baton keeps one server-side connection open so BEGIN ... COMMIT spans requests.
Turso gives a transaction about 5 seconds, which ELEVIA's short requests fit.
"""
from __future__ import annotations

import base64
import sqlite3
from typing import Any, Optional, Sequence

import httpx

# Tests can inject a fake HTTP transport here.
_transport: Optional[httpx.BaseTransport] = None

_WRITE_PREFIXES = ("INSERT", "UPDATE", "DELETE", "REPLACE")


def set_transport(t: Optional[httpx.BaseTransport]) -> None:
    global _transport
    _transport = t


def http_url(url: str) -> str:
    url = url.strip().rstrip("/")
    if url.startswith("libsql://"):
        url = "https://" + url[len("libsql://"):]
    return url


class Row(tuple):
    """Tuple that also supports row["column"] and dict(row), like sqlite3.Row."""

    def __new__(cls, values, keys):
        obj = super().__new__(cls, values)
        obj._keys = keys
        return obj

    def keys(self):
        return list(self._keys)

    def __getitem__(self, k):
        if isinstance(k, str):
            try:
                return tuple.__getitem__(self, self._keys.index(k))
            except ValueError:
                raise IndexError(f"No column named {k}") from None
        return tuple.__getitem__(self, k)


class Cursor:
    def __init__(self, result: dict):
        cols = [c.get("name") for c in result.get("cols", [])]
        self._rows = [Row([_decode(v) for v in r], cols) for r in result.get("rows", [])]
        self.rowcount = int(result.get("affected_row_count") or 0)
        lid = result.get("last_insert_rowid")
        self.lastrowid = int(lid) if lid not in (None, "") else None
        self._i = 0

    def fetchone(self):
        if self._i >= len(self._rows):
            return None
        r = self._rows[self._i]
        self._i += 1
        return r

    def fetchall(self):
        rest = self._rows[self._i:]
        self._i = len(self._rows)
        return rest

    def __iter__(self):
        return iter(self.fetchall())


def _encode(v: Any) -> dict:
    if v is None:
        return {"type": "null"}
    if isinstance(v, bool):
        return {"type": "integer", "value": "1" if v else "0"}
    if isinstance(v, int):
        return {"type": "integer", "value": str(v)}
    if isinstance(v, float):
        return {"type": "float", "value": v}
    if isinstance(v, (bytes, bytearray)):
        return {"type": "blob", "base64": base64.b64encode(bytes(v)).decode()}
    return {"type": "text", "value": str(v)}


def _decode(v: dict) -> Any:
    t = v.get("type")
    if t == "null":
        return None
    if t == "integer":
        return int(v["value"])
    if t == "float":
        return float(v["value"])
    if t == "blob":
        return base64.b64decode(v.get("base64", ""))
    return v.get("value")


def _raise(err: dict) -> None:
    msg = (err or {}).get("message", "Turso error")
    if "UNIQUE" in msg or "constraint" in msg.lower():
        raise sqlite3.IntegrityError(msg)
    raise sqlite3.OperationalError(msg)


def split_script(script: str) -> list[str]:
    stmts, buf = [], ""
    for line in script.splitlines(keepends=True):
        buf += line
        if sqlite3.complete_statement(buf):
            if buf.strip():
                stmts.append(buf.strip())
            buf = ""
    if buf.strip():
        stmts.append(buf.strip())
    return [s for s in (_strip_comments(s) for s in stmts) if s]


def _strip_comments(s: str) -> str:
    lines = [ln for ln in s.splitlines() if not ln.strip().startswith("--")]
    return "\n".join(lines).strip()


class TursoConnection:
    row_factory = None  # accepted for sqlite3 compatibility; rows always support names

    def __init__(self, url: str, token: str, timeout: float = 10.0):
        self._url = http_url(url)
        self._client = httpx.Client(timeout=timeout, transport=_transport,
                                    headers={"Authorization": f"Bearer {token}"})
        self._baton: Optional[str] = None
        self.in_transaction = False

    def _pipeline(self, requests: list[dict]) -> list[dict]:
        try:
            r = self._client.post(f"{self._url}/v2/pipeline", json={"baton": self._baton, "requests": requests})
        except httpx.HTTPError as e:
            raise sqlite3.OperationalError(f"Database unreachable: {type(e).__name__}") from None
        if r.status_code >= 400:
            raise sqlite3.OperationalError(f"Database HTTP {r.status_code}")
        body = r.json()
        self._baton = body.get("baton")
        if body.get("base_url"):
            self._url = http_url(body["base_url"])
        out = []
        for res in body.get("results", []):
            if res.get("type") == "error":
                _raise(res.get("error"))
            out.append(res.get("response", {}))
        return out

    @staticmethod
    def _stmt(sql: str, params: Sequence[Any] = ()) -> dict:
        return {"type": "execute", "stmt": {"sql": sql, "args": [_encode(p) for p in params]}}

    def execute(self, sql: str, params: Sequence[Any] = ()) -> Cursor:
        reqs = []
        is_write = sql.lstrip().upper().startswith(_WRITE_PREFIXES)
        if is_write and not self.in_transaction:
            reqs.append(self._stmt("BEGIN"))  # like sqlite3: implicit transaction before a write
        reqs.append(self._stmt(sql, tuple(params)))
        try:
            responses = self._pipeline(reqs)
        except sqlite3.Error:
            if is_write and self._baton:
                self.in_transaction = True  # BEGIN ran; the caller's rollback() will end it
            raise
        if is_write:
            self.in_transaction = True
        return Cursor(responses[-1].get("result", {}))

    def executescript(self, script: str) -> None:
        self.commit()
        stmts = split_script(script)
        if stmts:
            self._pipeline([self._stmt(s) for s in stmts])

    def commit(self) -> None:
        if self.in_transaction:
            self._pipeline([self._stmt("COMMIT")])
            self.in_transaction = False

    def rollback(self) -> None:
        if self.in_transaction:
            try:
                self._pipeline([self._stmt("ROLLBACK")])
            finally:
                self.in_transaction = False

    def close(self) -> None:
        try:
            if self._baton:
                self._pipeline([{"type": "close"}])
        except sqlite3.Error:
            pass
        finally:
            self._client.close()
