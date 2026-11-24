"""Vercel build step (runs after dependencies are installed, before the deployment goes live).

Checks the curriculum, then, ONLY for production deployments with ELEVIA_DEMO_RESET_ON_DEPLOY=1 and a Turso
database, resets the fictional Class 9 demo (demo-registered records only; see scripts/demo_sync.py).
So a production redeploy gives judges a fresh, complete six-month demo. Nothing secret is printed.

A failed demo reset is reported in the build log but doesn't fail the deployment: the app itself still works,
and the previous demo data stays as it was (the change is applied in one transaction).
"""
import os
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))


def _report_region() -> None:
    """Print the database region and the round-trip time from the build machine (no names, no secrets)."""
    import re
    m = re.search(r"\.((?:aws|gcp|fly)-[a-z0-9-]+)\.turso\.io", os.getenv("TURSO_DATABASE_URL", ""))
    try:
        from backend import db
        conn = db.connect()
        try:
            conn.execute("SELECT 1")
            t = time.time()
            for _ in range(5):
                conn.execute("SELECT 1")
            ms = (time.time() - t) / 5 * 1000
        finally:
            conn.close()
        print(f"ELEVIA build: database region {m.group(1) if m else 'unknown'}; "
              f"{ms:.0f} ms per query from build region {os.getenv('VERCEL_REGION', '?')}.")
    except Exception as e:  # informational only
        print(f"ELEVIA build: database check failed ({type(e).__name__}).")


def main() -> int:
    from backend.content import validate_all
    validate_all()
    print("ELEVIA build: curriculum valid.")
    env = os.getenv("VERCEL_ENV", "")
    wanted = os.getenv("ELEVIA_DEMO_RESET_ON_DEPLOY", "").strip().lower() in ("1", "true", "yes")
    if env != "production" or not wanted:
        print(f"ELEVIA build: demo reset skipped (VERCEL_ENV={env or 'unset'}, "
              f"ELEVIA_DEMO_RESET_ON_DEPLOY={'on' if wanted else 'off'}).")
        return 0
    if not os.getenv("TURSO_DATABASE_URL", "").strip():
        print("ELEVIA build: demo reset skipped: no TURSO_DATABASE_URL in this environment.")
        return 0
    _report_region()
    started = time.time()
    try:
        from demo_sync import fast_reset
        out = fast_reset()
        out.pop("password", None)
        changed = sum(v["inserted"] for v in out["applied"].values())
        print(f"ELEVIA build: demo reset done in {time.time() - started:.0f}s: six months "
              f"{out['period_start']} to {out['reference_date']}, {changed} demo rows written.")
    except BaseException as e:  # SystemExit included: never fail the deployment because of the demo
        print(f"ELEVIA build: DEMO RESET FAILED ({type(e).__name__}: {e}). Previous demo data left unchanged.")
        traceback.print_exc(limit=3)
    return 0


if __name__ == "__main__":
    sys.exit(main())
