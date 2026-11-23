"""The one place ELEVIA reads the current time.

Normally this is just the real UTC time. The demo seed script (scripts/demo.py) is the only caller of
`simulated()`: it runs the REAL learning workflow on a simulated calendar so a six-month history gets
natural timestamps (and retest delays are honoured, not skipped). The override lives in this process only;
no request, header or setting can change it, and it is always restored when the block ends.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, Optional

_override: Optional[datetime] = None


def now() -> datetime:
    """Current UTC time, to the second."""
    t = _override if _override is not None else datetime.now(timezone.utc)
    return t.replace(microsecond=0)


def is_simulated() -> bool:
    return _override is not None


class SimClock:
    """Handle returned by simulated(); move the clock with set() / advance()."""

    def set(self, when: datetime) -> None:
        global _override
        if when.tzinfo is None:
            raise ValueError("simulated time must be timezone-aware")
        _override = when.astimezone(timezone.utc)

    def advance(self, **delta) -> None:
        from datetime import timedelta
        self.set(now() + timedelta(**delta))


@contextmanager
def simulated(start: datetime) -> Iterator[SimClock]:
    """Seeding only. Everything inside the block sees `start` (then whatever set()/advance() choose) as 'now'."""
    global _override
    previous = _override
    clk = SimClock()
    clk.set(start)
    try:
        yield clk
    finally:
        _override = previous
