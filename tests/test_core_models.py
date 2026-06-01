from datetime import datetime, timezone, timedelta
from koraku.core.models import utcnow, as_utc


def test_utcnow():
    """Test that utcnow returns a timezone-aware UTC datetime close to the current time."""
    now = utcnow()

    assert isinstance(now, datetime)
    assert now.tzinfo is timezone.utc

    # Check that it's close to actual current UTC time (within 1 second)
    actual_now = datetime.now(timezone.utc)
    delta = abs(actual_now - now)
    assert delta < timedelta(seconds=1)


def test_as_utc_with_naive_datetime():
    """Test that as_utc converts a naive datetime to a timezone-aware UTC datetime."""
    naive_dt = datetime(2023, 1, 1, 12, 0, 0)
    assert naive_dt.tzinfo is None

    utc_dt = as_utc(naive_dt)

    assert utc_dt.tzinfo is timezone.utc
    assert utc_dt.year == 2023
    assert utc_dt.month == 1
    assert utc_dt.day == 1
    assert utc_dt.hour == 12
    assert utc_dt.minute == 0
    assert utc_dt.second == 0


def test_as_utc_with_aware_datetime():
    """Test that as_utc converts a timezone-aware datetime to UTC correctly."""
    # Create a timezone with a 5 hour offset (e.g., EST)
    est_tz = timezone(timedelta(hours=-5))
    aware_dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=est_tz)

    utc_dt = as_utc(aware_dt)

    assert utc_dt.tzinfo is timezone.utc
    # 12:00 EST (-5) is 17:00 UTC
    assert utc_dt.hour == 17
    assert utc_dt.year == 2023
    assert utc_dt.month == 1
    assert utc_dt.day == 1


def test_as_utc_with_already_utc_datetime():
    """Test that as_utc leaves an already UTC datetime unchanged."""
    already_utc_dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    utc_dt = as_utc(already_utc_dt)

    assert utc_dt.tzinfo is timezone.utc
    assert utc_dt == already_utc_dt
    assert utc_dt.hour == 12
