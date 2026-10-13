"""Room 25's lockbox: nothing from LOCKBOX_START onward is used in development.

Every fetcher cuts at DEV_END; every scorer calls assert_dev() on its timestamps.
Opening the lockbox is a written act in STATE, with a frozen candidate's commit.
"""
from datetime import datetime, timezone

LOCKBOX_START = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
# Lockbox 2 (set 21:17 UTC 12 Oct 2026): 1986-01-01 .. 1995-05-31; development starts 1995-06-01
LOCKBOX2_START = datetime(1986, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
LOCKBOX2_END = datetime(1995, 5, 31, 23, 59, 59, tzinfo=timezone.utc)
DEV_START = datetime(1995, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
DEV_END = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)


def assert_dev(times):
    """Raise if any timestamp (datetime, date, or ISO string) is in the lockbox."""
    for t in times:
        if isinstance(t, str):
            t = datetime.fromisoformat(t.replace("Z", "+00:00"))
        if not hasattr(t, "hour"):
            t = datetime(t.year, t.month, t.day, tzinfo=timezone.utc)
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        if t >= LOCKBOX_START:
            raise RuntimeError(f"lockbox breach: {t.isoformat()}")
        if t < DEV_START:
            raise RuntimeError(f"lockbox-2 breach (before 1995-06-01): {t.isoformat()}")
