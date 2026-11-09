"""Thin client for the ELEVIA FastAPI backend.

By default it calls the backend over HTTP (ELEVIA_API_URL, default
http://localhost:8000). Set ELEVIA_EMBEDDED=1 to run the same FastAPI app
in-process instead (handy for single-service free hosting such as Streamlit
Community Cloud). Either way every request goes through the FastAPI routes.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional

import httpx

API_URL = os.getenv("ELEVIA_API_URL", "http://localhost:8000").rstrip("/")
EMBEDDED = os.getenv("ELEVIA_EMBEDDED", "").lower() in ("1", "true", "yes")


class ApiError(Exception):
    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status


_client = None


def _get_client():
    global _client
    if _client is None:
        if EMBEDDED:
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from fastapi.testclient import TestClient
            from backend.main import app
            _client = TestClient(app)
            _client.__enter__()  # runs startup (DB init, content validation)
        else:
            _client = httpx.Client(base_url=API_URL, timeout=60)
    return _client


def _request(method: str, path: str, *, json: Any = None, params: dict | None = None,
             pin: Optional[str] = None) -> Any:
    headers = {"X-Teacher-Pin": pin} if pin else {}
    try:
        r = _get_client().request(method, path, json=json, params=params, headers=headers)
    except httpx.HTTPError:
        raise ApiError(f"Can't reach the ELEVIA backend at {API_URL}. Is it running? "
                       "(uvicorn backend.main:app --port 8000)")
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail")
        except ValueError:
            detail = r.text
        if isinstance(detail, list):  # pydantic validation errors
            detail = "; ".join(f"{'.'.join(str(x) for x in d.get('loc', [])[1:])}: {d.get('msg')}" for d in detail)
        raise ApiError(str(detail or f"HTTP {r.status_code}"), r.status_code)
    return r.json()


def get(path: str, params: dict | None = None, pin: Optional[str] = None) -> Any:
    return _request("GET", path, params=params, pin=pin)


def post(path: str, body: Any = None, pin: Optional[str] = None) -> Any:
    return _request("POST", path, json=body or {}, pin=pin)
