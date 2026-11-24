"""Fast demo reset for Turso: same result as the normal reset, one transaction, real users untouched."""
import importlib.util
import sqlite3
import sys
from datetime import date
from pathlib import Path

import httpx
import pytest

from tests.fake_turso import FakeTurso
from tests.test_accounts import H, make_learner

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
REF = date(2026, 11, 24)


def _load(name):
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def turso_db(tmp_path, monkeypatch):
    """Route the app through the Turso connector to a fake server, even when the suite runs on SQLite."""
    from backend import db, turso
    fake = FakeTurso(str(tmp_path / "remote.db"))
    turso.set_transport(httpx.MockTransport(fake.handle))
    monkeypatch.setenv("TURSO_DATABASE_URL", "libsql://elevia-sync-test.turso.io")
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "test-token")
    db.init_db()
    yield tmp_path / "remote.db"
    turso.set_transport(None)


def q(path, sql, *a):
    c = sqlite3.connect(path)
    try:
        return c.execute(sql, a).fetchall()
    finally:
        c.close()


def test_fast_reset_builds_the_demo_and_keeps_real_users(client, turso_db, monkeypatch):
    sync = _load("demo_sync")
    real_tok, real_id = make_learner(client, email="real.person@example.org")
    client.post("/learn/start", json={"grade": 9, "topic_id": "loops"}, headers=H(real_tok))
    real_before = q(turso_db, "SELECT * FROM users WHERE id=?", real_id)
    real_cases = q(turso_db, "SELECT * FROM cases WHERE student_id=?", real_id)

    out = sync.fast_reset(reference_date=REF, password="Test-Demo-Pass-42")
    assert out["deleted"] == {} or not any(out["deleted"].values())
    assert q(turso_db, "SELECT COUNT(*) FROM demo_registry WHERE kind='user'")[0][0] == 13
    assert q(turso_db, "SELECT COUNT(*) FROM demo_profiles WHERE student_code='DEMO-09-001'")[0][0] == 1
    assert q(turso_db, "SELECT COUNT(*) FROM responses")[0][0] > 300           # the class's six months of answers
    assert q(turso_db, "SELECT COUNT(*) FROM cases WHERE stage='teacher_review'")[0][0] == 3
    first = {t: q(turso_db, f"SELECT COUNT(*) FROM {t}")[0][0] for t in ("users", "cases", "responses", "agent_runs")}

    # a judge changes the demo, then the deployment resets it again
    monkeypatch.setenv("ELEVIA_DEMO_MODE", "1")
    fr = client.post("/demo/login", json={"slug": "fresh"}, headers={"X-Elevia-Web": "1"}).cookies.get("elevia_session")
    client.post("/learn/start", json={"grade": 7, "topic_id": "decimals"}, headers=H(fr))
    out = sync.fast_reset(reference_date=REF, password="Test-Demo-Pass-42")
    assert out["deleted"]["users"] == 13
    again = {t: q(turso_db, f"SELECT COUNT(*) FROM {t}")[0][0] for t in first}
    assert again == first                                       # same known state every time
    assert q(turso_db, "SELECT * FROM users WHERE id=?", real_id) == real_before
    assert q(turso_db, "SELECT * FROM cases WHERE student_id=?", real_id) == real_cases
    # the app reads the result normally
    d = client.get("/demo/accounts").json()
    assert d["ready"] and all(a["available"] for a in d["accounts"] if a["slug"] in ("riya", "fresh"))


def test_fast_reset_refuses_to_touch_non_demo_users(turso_db, tmp_path):
    sync = _load("demo_sync")
    from backend import db
    remote = db.connect()
    try:
        sync.dump(remote, str(tmp_path / "before.db"))
    finally:
        remote.close()
    c = sqlite3.connect(tmp_path / "before.db")
    c.execute("PRAGMA ignore_check_constraints = ON")
    cols = [r[1] for r in c.execute("PRAGMA table_info(users)") if r[3] and r[1] != "id"]   # NOT NULL columns
    c.execute(f"INSERT INTO users(id,{','.join(cols)}) VALUES (99,{','.join('?' * len(cols))})", ["x"] * len(cols))
    c.commit()
    c.close()
    rid = q(tmp_path / "before.db", "SELECT rowid FROM users WHERE id=99")[0][0]
    changes = {"new_tables": [], "tables": {"users": {"cols": [], "delete": [rid], "insert": []}}}
    with pytest.raises(RuntimeError, match="non-demo users"):
        sync.check(str(tmp_path / "before.db"), changes)


def test_build_step_resets_demo_only_in_production_when_asked(turso_db, monkeypatch, capsys):
    build = _load("vercel_build")
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.setenv("ELEVIA_DEMO_RESET_ON_DEPLOY", "1")
    assert build.main() == 0
    assert "skipped" in capsys.readouterr().out
    assert q(turso_db, "SELECT COUNT(*) FROM demo_registry")[0][0] == 0
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.setenv("ELEVIA_DEMO_REFERENCE_DATE", REF.isoformat())
    assert build.main() == 0
    log = capsys.readouterr().out
    assert "demo reset done" in log and "password" not in log.lower()
    assert q(turso_db, "SELECT COUNT(*) FROM demo_registry WHERE kind='user'")[0][0] == 13
