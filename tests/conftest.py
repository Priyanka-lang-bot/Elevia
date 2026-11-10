import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    """Every test gets its own SQLite file and mock LLM mode."""
    monkeypatch.setenv("ELEVIA_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("TEACHER_PIN", "9999")
    monkeypatch.setenv("RETEST_DELAY_HOURS", "24")
    monkeypatch.setenv("ALLOW_EARLY_RETEST", "true")
    import os
    from backend import db, llm, turso
    if os.getenv("ELEVIA_TEST_TURSO") == "1":  # run the suite through the Turso connector
        import httpx
        from tests.fake_turso import FakeTurso
        fake = FakeTurso(str(tmp_path / "test.db"))
        turso.set_transport(httpx.MockTransport(fake.handle))
        monkeypatch.setenv("TURSO_DATABASE_URL", "libsql://elevia-test.turso.io")
        monkeypatch.setenv("TURSO_AUTH_TOKEN", "test-token")
    db.init_db()
    llm.set_transport(None)
    yield
    llm.set_transport(None)


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from backend.main import app
    with TestClient(app) as c:
        # These tests pass sessions explicitly in headers; drop cookies so identities never leak between calls.
        c.event_hooks["response"].append(lambda r: c.cookies.clear())
        yield c


@pytest.fixture
def browser():
    """A client that keeps cookies, like a real browser on ELEVIA's own page."""
    from fastapi.testclient import TestClient
    from backend.main import app
    with TestClient(app, base_url="https://testserver") as c:
        yield c


TEACHER = {"X-Teacher-Pin": "9999"}
