"""Create SAMPLE students for demonstration (see backend/sample_data.py).

Run:  python seed.py          (adds sample students if they don't exist)
      python seed.py --reset  (deletes the database first)
"""
import argparse
import os

from backend.config import get_settings
from backend.sample_data import seed

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="delete the database first")
    args = ap.parse_args()
    if args.reset and os.path.exists(get_settings().db_path):
        os.remove(get_settings().db_path)
    seed()
