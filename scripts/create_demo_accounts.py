"""Kept for older instructions. Same as: python scripts/demo.py seed (see scripts/demo.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import demo  # noqa: E402

if __name__ == "__main__":
    print("Demo created:", demo.seed(activity=True))
