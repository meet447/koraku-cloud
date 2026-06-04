"""Shared presentation helpers for automation rows (HTTP API + agent tools)."""

from __future__ import annotations

import asyncio
from typing import Any

from koraku_cloud.automations.cron_next import compute_next_cron_fire
from koraku_cloud.automations.schedule import schedule_label


def automation_status_line(row: dict[str, Any]) -> str:
    if row.get("status") == "paused":
        return "Paused"
    if row.get("current_run_id"):
        return "Running"
    if row.get("trigger_mode") == "event":
        if row.get("event_source") == "composio":
            return "Waiting for app event"
        return "Waiting for event"
    if row.get("trigger_mode") == "scheduled":
        return "Scheduled"
    return ""


def automation_health_line(row: dict[str, Any]) -> str | None:
    failures = int(row.get("consecutive_failures") or 0)
    threshold = int(row.get("max_failures_before_pause") or 3)
    if failures <= 0:
        return None
    if threshold > 0 and failures >= threshold:
        return f"Degraded ({failures} failures)"
    if failures >= 2:
        return f"{failures} recent failures"
    return None


async def enrich_automation_row(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["status_line"] = automation_status_line(row)
    health = automation_health_line(row)
    if health:
        out["health_line"] = health
    preset = row.get("schedule_preset")
    cron = row.get("cron_expression")
    if isinstance(preset, dict) or cron:
        out["schedule_label"] = schedule_label(
            preset if isinstance(preset, dict) else None,
            str(cron) if cron else None,
        )
    if (
        row.get("trigger_mode") == "scheduled"
        and row.get("cron_expression")
        and row.get("timezone")
    ):
        nxt = await asyncio.to_thread(
            compute_next_cron_fire,
            str(row["cron_expression"]),
            str(row["timezone"]),
        )
        if nxt:
            out["next_run_at_computed"] = nxt.isoformat()
    return out


async def enrich_automation_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []

    def _process_all(rows_batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
        results = []
        for row in rows_batch:
            out = dict(row)
            out["status_line"] = automation_status_line(row)
            health = automation_health_line(row)
            if health:
                out["health_line"] = health
            preset = row.get("schedule_preset")
            cron = row.get("cron_expression")
            if isinstance(preset, dict) or cron:
                out["schedule_label"] = schedule_label(
                    preset if isinstance(preset, dict) else None,
                    str(cron) if cron else None,
                )
            if (
                row.get("trigger_mode") == "scheduled"
                and row.get("cron_expression")
                and row.get("timezone")
            ):
                nxt = compute_next_cron_fire(
                    str(row["cron_expression"]),
                    str(row["timezone"]),
                )
                if nxt:
                    out["next_run_at_computed"] = nxt.isoformat()
            results.append(out)
        return results

    return await asyncio.to_thread(_process_all, rows)
