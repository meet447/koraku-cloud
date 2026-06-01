"""Shared presentation helpers for automation rows (HTTP API + agent tools)."""

from __future__ import annotations

import asyncio
from typing import Any

from koraku.automations.cron_next import compute_next_cron_fire


def automation_status_line(row: dict[str, Any]) -> str:
    if row.get("status") == "paused":
        return "Paused"
    if row.get("trigger_mode") == "event":
        return "Waiting for event"
    if row.get("trigger_mode") == "scheduled":
        return "Scheduled"
    return ""


async def enrich_automation_row(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out["status_line"] = automation_status_line(row)
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
    """Enrich multiple automation rows efficiently using a single thread pool task."""
    if not rows:
        return []

    def _process_all(rows_batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
        results = []
        for row in rows_batch:
            out = dict(row)
            out["status_line"] = automation_status_line(row)
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
