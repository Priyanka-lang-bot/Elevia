"""Fast demo reset for a Turso (hosted SQLite) database.

The normal reset (scripts/demo.py reset) runs the real product code and issues about 25,000 SQL statements.
Turso answers one statement per HTTP request, so running it straight against Turso takes far too long.

This module gets the same result quickly and safely:

1. make sure the tables exist on Turso (CREATE TABLE IF NOT EXISTS; changes nothing that exists);
2. copy every table from Turso into a local SQLite file (this copy is also the backup of the "before" state);
3. run the ordinary demo reset (delete demo rows, then seed six months) against a second local copy;
4. compare the two copies and check that every deleted user/school was a registered demo record;
5. apply only the differences to Turso in ONE transaction (all or nothing; a clash rolls everything back).

Only rows the real reset deleted or created are touched, so non-demo data is left exactly as it was.
"""
import os
import shutil
import sqlite3
import sys
import tempfile
from contextlib import contextmanager
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend import db  # noqa: E402

CHUNK = 150


def _tables(conn) -> list[tuple[str, str]]:
    return [(r[0], r[1]) for r in conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
        "AND name NOT LIKE '_litestream%' AND name NOT LIKE 'libsql_%' ORDER BY name").fetchall()]


def _indexes(conn) -> list[str]:
    return [r[0] for r in conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL").fetchall()]


def _cols(conn, table: str) -> list[str]:
    return [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")').fetchall()]


def dump(remote, path: str) -> dict:
    """Copy all tables (with rowids) from the remote connection into a new local SQLite file."""
    local = sqlite3.connect(path)
    counts = {}
    try:
        for name, sql in _tables(remote):
            if "WITHOUT ROWID" in (sql or "").upper():
                raise RuntimeError(f"Table {name} has no rowid; fast reset can't copy it safely.")
            local.execute(sql)
            cols = _cols(remote, name)
            rows = remote.execute(f'SELECT rowid, * FROM "{name}"').fetchall()
            ph = ",".join("?" * (len(cols) + 1))
            collist = ",".join(f'"{c}"' for c in cols)
            local.executemany(f'INSERT INTO "{name}"(rowid,{collist}) VALUES ({ph})',
                              [tuple(r[i] for i in range(len(cols) + 1)) for r in rows])
            counts[name] = len(rows)
        for sql in _indexes(remote):
            local.execute(sql)
        if remote.execute("SELECT 1 FROM sqlite_master WHERE name='sqlite_sequence'").fetchone():
            # keep AUTOINCREMENT counters, so new demo ids never reuse ids of earlier deleted rows
            for name, seq in remote.execute("SELECT name, seq FROM sqlite_sequence").fetchall():
                local.execute("UPDATE sqlite_sequence SET seq=max(seq, ?) WHERE name=?", (seq, name))
                if not local.execute("SELECT changes()").fetchone()[0]:
                    local.execute("INSERT INTO sqlite_sequence(name, seq) VALUES (?, ?)", (name, seq))
        local.commit()
    finally:
        local.close()
    return counts


def _rows(conn, table: str, cols: list[str]) -> dict:
    collist = ",".join(f'"{c}"' for c in cols)
    return {r[0]: tuple(r[1:]) for r in conn.execute(f'SELECT rowid,{collist} FROM "{table}"').fetchall()}


def diff(before_path: str, after_path: str) -> dict:
    """Per table: rows to delete (rowids) and rows to insert (rowid + values)."""
    b, a = sqlite3.connect(before_path), sqlite3.connect(after_path)
    try:
        before_tables = {n for n, _ in _tables(b)}
        new_tables = [(n, s) for n, s in _tables(a) if n not in before_tables]
        out = {"new_tables": new_tables, "tables": {}}
        for name, _ in _tables(a):
            cols = _cols(a, name)
            old = _rows(b, name, cols) if name in before_tables else {}
            new = _rows(a, name, cols)
            deleted = [rid for rid, v in old.items() if new.get(rid) != v]
            inserted = [(rid, v) for rid, v in new.items() if old.get(rid) != v]
            if deleted or inserted:
                out["tables"][name] = {"cols": cols, "delete": deleted, "insert": inserted}
        return out
    finally:
        b.close()
        a.close()


def check(before_path: str, changes: dict) -> None:
    """Refuse to apply anything that would delete a user or school that was not a registered demo record."""
    b = sqlite3.connect(before_path)
    try:
        has_registry = b.execute("SELECT 1 FROM sqlite_master WHERE name='demo_registry'").fetchone()
        reg = {"user": set(), "school": set()}
        if has_registry:
            for kind, ref in b.execute("SELECT kind, ref_id FROM demo_registry").fetchall():
                reg.setdefault(kind, set()).add(ref)
        for table, kind in (("users", "user"), ("schools", "school")):
            t = changes["tables"].get(table)
            if not t:
                continue
            ids = set()
            for rid in t["delete"]:
                row = b.execute(f"SELECT id FROM {table} WHERE rowid=?", (rid,)).fetchone()
                ids.add(row[0])
            outsiders = ids - reg.get(kind, set())
            if outsiders:
                raise RuntimeError(f"Refusing: the reset would change non-demo {table} {sorted(outsiders)}.")
    finally:
        b.close()


def apply(remote, changes: dict) -> dict:
    """Apply the differences on the remote connection in one transaction."""
    stmts = [(sql, ()) for _, sql in changes["new_tables"]]
    stmts += [("BEGIN", ()), ("PRAGMA defer_foreign_keys = ON", ())]
    for name, t in changes["tables"].items():
        stmts += [(f'DELETE FROM "{name}" WHERE rowid=?', (rid,)) for rid in t["delete"]]
    for name, t in changes["tables"].items():
        collist = ",".join(f'"{c}"' for c in t["cols"])
        ph = ",".join("?" * (len(t["cols"]) + 1))
        stmts += [(f'INSERT INTO "{name}"(rowid,{collist}) VALUES ({ph})', (rid, *v)) for rid, v in t["insert"]]
    stmts.append(("COMMIT", ()))
    try:
        for i in range(0, len(stmts), CHUNK):
            remote._pipeline([remote._stmt(s, p) for s, p in stmts[i:i + CHUNK]])
    except Exception:
        try:
            remote._pipeline([remote._stmt("ROLLBACK")])
        except Exception:
            pass
        raise
    return {name: {"deleted": len(t["delete"]), "inserted": len(t["insert"])}
            for name, t in changes["tables"].items()}


@contextmanager
def _local_database(path: str):
    """Point the app at a local SQLite file for the duration (restores the Turso settings afterwards)."""
    saved = {k: os.environ.get(k) for k in ("TURSO_DATABASE_URL", "ELEVIA_DB_PATH")}
    os.environ.pop("TURSO_DATABASE_URL", None)
    os.environ["ELEVIA_DB_PATH"] = path
    try:
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def fast_reset(reference_date: date | None = None, password: str | None = None,
               keep_backup_dir: str | None = None) -> dict:
    if not db.using_turso():
        raise SystemExit("Fast reset is for Turso. For local SQLite use: python scripts/demo.py reset")
    import demo  # scripts/demo.py
    db.init_db()                                   # CREATE IF NOT EXISTS on Turso
    work = Path(tempfile.mkdtemp(prefix="elevia-demo-"))
    before, after = str(work / "before.db"), str(work / "after.db")
    remote = db.connect()
    try:
        counts = dump(remote, before)
    finally:
        remote.close()
    shutil.copyfile(before, after)
    with _local_database(after):
        out = demo.reset(reference_date=reference_date, password=password)
    changes = diff(before, after)
    check(before, changes)
    remote = db.connect()
    try:
        applied = apply(remote, changes)
    finally:
        remote.close()
    if keep_backup_dir:
        Path(keep_backup_dir).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(before, Path(keep_backup_dir) / "turso-before-demo-reset.db")
    shutil.rmtree(work, ignore_errors=True)
    out["rows_before"] = sum(counts.values())
    out["applied"] = applied
    return out
