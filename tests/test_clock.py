"""The simulated clock is for the demo seed only: real time by default, always restored, never request-controlled."""
from datetime import datetime, timedelta, timezone

import pytest

from backend import clock, db
from backend.accounts import core


def test_real_time_by_default():
    assert not clock.is_simulated()
    assert abs((clock.now() - datetime.now(timezone.utc)).total_seconds()) < 5


def test_simulated_block_moves_every_clock_and_is_restored():
    start = datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc)
    with clock.simulated(start) as clk:
        assert db.now_iso() == "2026-06-01T09:00:00+00:00"
        assert core.utcnow() == start
        clk.advance(days=3, hours=2)
        assert db.now_iso() == "2026-06-04T11:00:00+00:00"
    assert not clock.is_simulated()


def test_restored_even_after_an_error():
    with pytest.raises(RuntimeError):
        with clock.simulated(datetime(2026, 1, 1, tzinfo=timezone.utc)):
            raise RuntimeError("boom")
    assert not clock.is_simulated()


def test_naive_time_is_refused():
    with pytest.raises(ValueError):
        with clock.simulated(datetime(2026, 1, 1)):
            pass


def test_no_route_can_change_the_clock(client):
    # every endpoint must leave the clock alone, whatever it is sent
    client.get("/health", headers={"X-Elevia-Clock": "2000-01-01"})
    client.get("/learn/catalog?now=2000-01-01")
    assert not clock.is_simulated()
    assert abs((clock.now() - datetime.now(timezone.utc)) ) < timedelta(seconds=5)
