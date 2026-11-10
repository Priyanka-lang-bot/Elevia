"""SQLite storage: the shared student learning record.

One connection per request/operation; JSON columns hold structured agent data.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator, Optional

from .config import get_settings

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL,
    grade INTEGER NOT NULL,
    is_sample INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

-- One learning case = one diagnose -> verify -> plan -> teach -> retest cycle.
CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    stage TEXT NOT NULL,
    diagnostic_set TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    closed_reason TEXT
);

CREATE TABLE IF NOT EXISTS assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('diagnostic','verification','practice','retest')),
    question_ids TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('open','completed')),
    available_at TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assessment_id INTEGER NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    question_id TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    answer_raw TEXT NOT NULL,
    is_correct INTEGER NOT NULL,
    pattern TEXT,
    hints_used INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    UNIQUE (assessment_id, question_id)
);

CREATE TABLE IF NOT EXISTS gaps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    skill_id TEXT NOT NULL,
    misconception TEXT,
    status TEXT NOT NULL CHECK (status IN ('suspected','confirmed','rejected','inconclusive','resolved','still_present')),
    confidence REAL NOT NULL,
    confidence_label TEXT NOT NULL,
    hypothesis TEXT NOT NULL,
    evidence TEXT NOT NULL,
    verified_by TEXT,
    verified_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    gap_id INTEGER NOT NULL REFERENCES gaps(id) ON DELETE CASCADE,
    focus_skill TEXT NOT NULL,
    path TEXT NOT NULL,
    rationale TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active','completed','cancelled','replaced')),
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    plan_id INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    skill_id TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skill_mastery (
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    skill_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('not_assessed','needs_practice','developing','mastered')),
    correct INTEGER NOT NULL DEFAULT 0,
    attempts INTEGER NOT NULL DEFAULT 0,
    updated_by TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (student_id, skill_id)
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    agent TEXT NOT NULL,
    step TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('running','succeeded','failed','skipped')),
    mode TEXT NOT NULL,
    input TEXT NOT NULL,
    output TEXT,
    error TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS teacher_overrides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    teacher_name TEXT NOT NULL,
    action TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cases_student ON cases(student_id);
CREATE INDEX IF NOT EXISTS idx_responses_student ON responses(student_id);
CREATE INDEX IF NOT EXISTS idx_runs_case ON agent_runs(case_id);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def using_turso() -> bool:
    import os
    return bool(os.getenv("TURSO_DATABASE_URL", "").strip())


def connect(db_path: Optional[str] = None):
    import os
    if db_path is None and using_turso():
        from .turso import TursoConnection
        conn = TursoConnection(os.environ["TURSO_DATABASE_URL"], os.getenv("TURSO_AUTH_TOKEN", ""))
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    conn = sqlite3.connect(db_path or get_settings().db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def transaction(db_path: Optional[str] = None) -> Iterator[sqlite3.Connection]:
    conn = connect(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Optional[str] = None) -> None:
    from .accounts.schema import ACCOUNTS_SCHEMA
    conn = connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.executescript(ACCOUNTS_SCHEMA)
        conn.commit()
    finally:
        conn.close()


JSON_COLUMNS = {"question_ids", "evidence", "path", "content", "input", "output"}


def row_to_dict(row: Optional[sqlite3.Row]) -> Optional[dict[str, Any]]:
    if row is None:
        return None
    d = dict(row)
    for k in JSON_COLUMNS & d.keys():
        if d[k] is not None:
            try:
                d[k] = json.loads(d[k])
            except (TypeError, json.JSONDecodeError):
                pass
    return d


def rows_to_dicts(rows) -> list[dict[str, Any]]:
    return [row_to_dict(r) for r in rows]


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)
