"""Compute next cron fire time (no SQLite dependency)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

log = logging.getLogger(__name__)
_UTC = timezone.utc


def compute_next_cron_fire(cron_expression: str, tz_name: str, base: datetime | None = None) -> datetime | None:
    """Return next UTC datetime after ``base`` for a 5-field cron in ``tz_name``."""
    try:
        from zoneinfo import ZoneInfo

        from croniter import croniter
    except ImportError:
        return None
    try:
        tz = ZoneInfo(tz_name.strip())
    except Exception:
        log.warning("invalid timezone for cron next: %r", tz_name)
        return None
    try:
        local_base = (base or datetime.now(_UTC)).astimezone(tz)
        it = croniter(cron_expression.strip(), local_base)
        nxt = it.get_next(datetime)
        if nxt.tzinfo is None:
            nxt = nxt.replace(tzinfo=tz)
        return nxt.astimezone(_UTC)
    except Exception:
        log.warning("invalid cron expression: %r (tz=%r)", cron_expression, tz_name)
        return None


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_UTC)
    return dt.astimezone(_UTC).isoformat()

