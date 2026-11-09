"""ELEVIA team command: add a subscribed school and invite its first admin.

    python scripts/create_school.py --name "Sunrise Public School" --admin-email head@school.in \
        --state Maharashtra --district Pune --days 365

Prints the admin's invitation link. With EMAIL_MODE=outbox (default) the email is
saved in the outbox instead of being sent. Use --demo to mark a clearly labelled
demo school. No school or referral code is ever hardcoded in the source.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import db  # noqa: E402
from backend.accounts import schools  # noqa: E402
from backend.accounts.errors import AccountError  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True)
    ap.add_argument("--admin-email", required=True)
    ap.add_argument("--state", default="")
    ap.add_argument("--district", default="")
    ap.add_argument("--udise", default=None, help="11-digit UDISE code, if known")
    ap.add_argument("--days", type=int, default=365, help="subscription length")
    ap.add_argument("--demo", action="store_true", help="mark as a demo school")
    a = ap.parse_args()
    db.init_db()
    try:
        with db.transaction() as conn:
            out = schools.create_school(conn, name=a.name, admin_email=a.admin_email, state=a.state,
                                        district=a.district, udise_code=a.udise, subscription_days=a.days,
                                        is_demo=a.demo)
    except AccountError as e:
        sys.exit(f"Error: {e}")
    print(f"School created (id {out['school_id']}). Admin invitation link:\n{out['invite_url']}")
