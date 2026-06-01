"""Validate automation trigger fields (cron + IANA timezone)."""
from __future__ import annotations

from datetime import datetime, timezone as tz

from croniter import croniter
from zoneinfo import ZoneInfo


def validate_cron_expression(cron: str) -> str:
    """Return normalized cron string or raise ValueError."""
    c = cron.strip()
    if len(c.split()) != 5:
        raise ValueError("cron_expression must have exactly 5 fields (min hour day month dow)")
    croniter(c, datetime.now(tz.utc))
    return c


try:
    from zoneinfo import ZoneInfoNotFoundError
except ImportError:
    # Fallback for Python 3.8
    ZoneInfoNotFoundError = Exception

def validate_timezone_iana(name: str) -> str:
    """Return normalized timezone name or raise ValueError."""
    try:
        z = ZoneInfo(name.strip())
        _ = str(z)
        return name.strip()
    except ZoneInfoNotFoundError as e:
        raise ValueError(f"Invalid IANA timezone: {name}") from e
