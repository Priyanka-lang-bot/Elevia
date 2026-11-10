"""A fake Turso HTTP server (POST /v2/pipeline) backed by a local SQLite file.

Lets the whole test suite run through backend/turso.py without a network.
It follows the documented request/response shapes; real Turso can still differ in
details this fake can't know, so a live check against a real database is needed too.
"""
import base64
import itertools
import json
import sqlite3

import httpx


class FakeTurso:
    def __init__(self, db_file: str):
        self.db_file = db_file
        self.streams: dict[str, sqlite3.Connection] = {}
        self._ids = itertools.count(1)

    @staticmethod
    def _arg(a):
        t = a["type"]
        if t == "null":
            return None
        if t == "integer":
            return int(a["value"])
        if t == "float":
            return float(a["value"])
        if t == "blob":
            return base64.b64decode(a["base64"])
        return a["value"]

    @staticmethod
    def _val(v):
        if v is None:
            return {"type": "null"}
        if isinstance(v, int):
            return {"type": "integer", "value": str(v)}
        if isinstance(v, float):
            return {"type": "float", "value": v}
        if isinstance(v, bytes):
            return {"type": "blob", "base64": base64.b64encode(v).decode()}
        return {"type": "text", "value": v}

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/pipeline", request.url.path
        assert request.headers.get("authorization", "").startswith("Bearer ")
        body = json.loads(request.content)
        baton = body.get("baton")
        conn = self.streams.pop(baton, None) if baton else None
        if baton and conn is None:
            return httpx.Response(400, json={"message": "stream expired"})
        if conn is None:
            conn = sqlite3.connect(self.db_file, isolation_level=None, timeout=10, check_same_thread=False)
        results, closed = [], False
        for req in body["requests"]:
            if req["type"] == "close":
                conn.close()
                closed = True
                results.append({"type": "ok", "response": {"type": "close"}})
                continue
            stmt = req["stmt"]
            try:
                cur = conn.execute(stmt["sql"], [self._arg(a) for a in stmt.get("args", [])])
                rows = cur.fetchall()
                cols = [{"name": d[0], "decltype": None} for d in (cur.description or [])]
                results.append({"type": "ok", "response": {"type": "execute", "result": {
                    "cols": cols, "rows": [[self._val(v) for v in r] for r in rows],
                    "affected_row_count": max(cur.rowcount, 0),
                    "last_insert_rowid": str(cur.lastrowid) if cur.lastrowid else None}}})
            except sqlite3.Error as e:
                results.append({"type": "error", "error": {"message": str(e), "code": "SQLITE_ERROR"}})
        new_baton = None
        if not closed:
            new_baton = f"b{next(self._ids)}"
            self.streams[new_baton] = conn
        return httpx.Response(200, json={"baton": new_baton, "base_url": None, "results": results})
