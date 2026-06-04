"""When scheduled/manual runs should be skipped instead of executed."""
from __future__ import annotations

from typing import Any

from koraku.core.config import settings


def failure_pause_threshold(auto: dict[str, Any]) -> int:
    raw = auto.get("max_failures_before_pause")
    try:
        n = int(raw) if raw is not None else 3
    except (TypeError, ValueError):
        n = 3
    if n <= 0:
        return 0
    return n


def evaluate_skip(
    auto: dict[str, Any],
    *,
    has_running_run: bool,
    lock_busy: bool,
) -> str | None:
    """Return a human-readable skip reason, or None to proceed."""
    if auto.get("status") != "active":
        return None
    if has_running_run or lock_busy:
        return "Skipped: a previous run is still in progress."
    threshold = failure_pause_threshold(auto)
    if threshold <= 0:
        return None
    try:
        failures = int(auto.get("consecutive_failures") or 0)
    except (TypeError, ValueError):
        failures = 0
    if failures >= threshold:
        return (
            f"Skipped: {failures} consecutive failures (limit {threshold}). "
            "Resume the automation after fixing the issue."
        )
    return None
