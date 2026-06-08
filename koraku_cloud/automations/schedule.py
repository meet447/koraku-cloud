"""Human-friendly schedule presets → 5-field cron expressions."""
from __future__ import annotations

from typing import Any

from koraku_cloud.automations.validation import validate_cron_expression


def _clamp_hour(h: int) -> int:
    return max(0, min(23, int(h)))


def _clamp_minute(m: int) -> int:
    return max(0, min(59, int(m)))


def preset_to_cron(preset: dict[str, Any]) -> str:
    """Convert a schedule preset dict to a cron string (raises ValueError)."""
    if not isinstance(preset, dict):
        raise ValueError("schedule_preset must be an object")
    kind = str(preset.get("kind") or "").strip().lower()
    if kind == "custom":
        cron = str(preset.get("cron_expression") or "").strip()
        if not cron:
            raise ValueError("custom schedule requires cron_expression")
        return validate_cron_expression(cron)
    if kind == "every_n_minutes":
        n = int(preset.get("every_n_minutes") or 30)
        n = max(1, min(59, n))
        return validate_cron_expression(f"*/{n} * * * *")
    if kind == "daily":
        h = _clamp_hour(int(preset.get("hour") if preset.get("hour") is not None else 9))
        m = _clamp_minute(int(preset.get("minute") if preset.get("minute") is not None else 0))
        return validate_cron_expression(f"{m} {h} * * *")
    if kind == "weekdays":
        h = _clamp_hour(int(preset.get("hour") if preset.get("hour") is not None else 9))
        m = _clamp_minute(int(preset.get("minute") if preset.get("minute") is not None else 0))
        return validate_cron_expression(f"{m} {h} * * 1-5")
    if kind == "weekly":
        h = _clamp_hour(int(preset.get("hour") if preset.get("hour") is not None else 9))
        m = _clamp_minute(int(preset.get("minute") if preset.get("minute") is not None else 0))
        dow = int(preset.get("day_of_week") if preset.get("day_of_week") is not None else 5)
        dow = max(0, min(6, dow))
        return validate_cron_expression(f"{m} {h} * * {dow}")
    raise ValueError(
        "schedule_preset.kind must be one of: every_n_minutes, daily, weekdays, weekly, custom"
    )


def cron_human_label(cron: str | None) -> str:
    """Turn common 5-field cron strings into short labels (fallback for custom cron)."""
    raw = (cron or "").strip()
    if not raw:
        return "—"
    parts = raw.split()
    if len(parts) != 5:
        return raw
    minute, hour, dom, month, dow = parts
    days = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")

    if (
        minute.startswith("*/")
        and hour == "*"
        and dom == "*"
        and month == "*"
        and dow == "*"
    ):
        step = minute[2:]
        if step.isdigit():
            n = int(step)
            return f"Every {n} minute" if n == 1 else f"Every {n} minutes"

    if (
        minute == "0"
        and hour.startswith("*/")
        and dom == "*"
        and month == "*"
        and dow == "*"
    ):
        step = hour[2:]
        if step.isdigit():
            n = int(step)
            return f"Every {n} hour" if n == 1 else f"Every {n} hours"

    if dom == "*" and month == "*" and minute.isdigit() and hour.isdigit():
        h, m = int(hour), int(minute)
        time_str = f"{h:02d}:{m:02d}"
        if dow == "*":
            return f"Daily at {time_str}"
        if dow == "1-5":
            return f"Weekdays at {time_str}"
        if dow.isdigit():
            d = int(dow)
            if 0 <= d <= 6:
                return f"Weekly {days[d]} {time_str}"

    return raw


def schedule_label(preset: dict[str, Any] | None, cron: str | None) -> str:
    if isinstance(preset, dict) and preset.get("kind"):
        kind = str(preset["kind"])
        if kind == "every_n_minutes":
            n = int(preset.get("every_n_minutes") or 30)
            return f"Every {n} minute" if n == 1 else f"Every {n} minutes"
        if kind == "daily":
            h, m = int(preset.get("hour") or 9), int(preset.get("minute") or 0)
            return f"Daily at {h:02d}:{m:02d}"
        if kind == "weekdays":
            h, m = int(preset.get("hour") or 9), int(preset.get("minute") or 0)
            return f"Weekdays at {h:02d}:{m:02d}"
        if kind == "weekly":
            days = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")
            d = int(preset.get("day_of_week") or 5)
            h, m = int(preset.get("hour") or 9), int(preset.get("minute") or 0)
            return f"Weekly {days[d]} {h:02d}:{m:02d}"
        if kind == "custom" and cron:
            return cron_human_label(str(cron))
    if cron:
        return cron_human_label(str(cron))
    return "—"
