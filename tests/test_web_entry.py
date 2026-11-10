"""The Vercel/web entry point (app.py): API under /api, email links keep their token."""
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def entry_client():
    import app as entry
    return TestClient(entry.app)


def test_api_is_under_api_and_root_keeps_query():
    with entry_client() as c:
        assert c.get("/api/health").json()["ok"] is True
        r = c.get("/?action=consent&token=abc123", follow_redirects=False)
        assert r.status_code == 307 and r.headers["location"] == "/index.html?action=consent&token=abc123"
        assert "ELEVIA" in c.get("/index.html").text


def test_legacy_unauthenticated_routes_off_on_vercel(monkeypatch):
    with entry_client() as c:
        assert c.get("/api/students").status_code == 200  # local default: on
        monkeypatch.setenv("VERCEL", "1")
        assert c.get("/api/students").status_code == 404
        assert c.get("/api/cases/1").status_code == 404
        assert c.get("/api/health").status_code == 200  # everything else still works
        monkeypatch.setenv("ELEVIA_LEGACY_API", "1")
        assert c.get("/api/students").status_code == 200
