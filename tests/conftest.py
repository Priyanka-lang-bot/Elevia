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
    from backend import db, llm
    db.init_db()
    llm.set_transport(None)
    yield
    llm.set_transport(None)


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from backend.main import app
    with TestClient(app) as c:
        yield c


TEACHER = {"X-Teacher-Pin": "9999"}
