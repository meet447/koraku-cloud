"""Non-blocking wrappers around Supabase-backed automation storage."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Literal

from koraku.automations import supabase_store
from koraku.automations.supabase_store import AutomationStatus, TriggerMode


async def init_db(_user_id: str) -> None:
    """Legacy no-op (SQLite init removed)."""
    return


async def list_automations(user_id: str) -> list[dict[str, Any]]:
    return await asyncio.to_thread(supabase_store.list_automations, user_id)


async def get_automation(user_id: str, automation_id: str) -> dict[str, Any] | None:
    return await asyncio.to_thread(supabase_store.get_automation, user_id, automation_id)


async def insert_automation(
    user_id: str,
    *,
    title: str,
    headline: str,
    natural_language_spec: str,
    trigger_mode: TriggerMode,
    status: AutomationStatus,
    timezone: str | None,
    cron_expression: str | None,
    event_display: str | None,
    toolkits: list[str],
) -> dict[str, Any]:
    def _go() -> dict[str, Any]:
        return supabase_store.insert_automation(
            user_id,
            title=title,
            headline=headline,
            natural_language_spec=natural_language_spec,
            trigger_mode=trigger_mode,
            status=status,
            timezone=timezone,
            cron_expression=cron_expression,
            event_display=event_display,
            toolkits=toolkits,
        )

    return await asyncio.to_thread(_go)


async def update_automation(
    user_id: str,
    automation_id: str,
    *,
    title: str | None = None,
    headline: str | None = None,
    natural_language_spec: str | None = None,
    status: AutomationStatus | None = None,
    timezone: str | None = None,
    cron_expression: str | None = None,
    event_display: str | None = None,
    toolkits: list[str] | None = None,
) -> dict[str, Any] | None:
    def _go() -> dict[str, Any] | None:
        return supabase_store.update_automation(
            user_id,
            automation_id,
            title=title,
            headline=headline,
            natural_language_spec=natural_language_spec,
            status=status,
            timezone=timezone,
            cron_expression=cron_expression,
            event_display=event_display,
            toolkits=toolkits,
        )

    return await asyncio.to_thread(_go)


async def delete_automation(user_id: str, automation_id: str) -> bool:
    return await asyncio.to_thread(supabase_store.delete_automation, user_id, automation_id)


async def list_runs(user_id: str, automation_id: str, limit: int = 50) -> list[dict[str, Any]]:
    return await asyncio.to_thread(supabase_store.list_runs, user_id, automation_id, limit)


async def insert_run_start(user_id: str, automation_id: str, *, trigger_summary: str) -> str:
    return await asyncio.to_thread(
        supabase_store.insert_run_start, user_id, automation_id, trigger_summary=trigger_summary
    )


async def finish_run(
    user_id: str,
    run_id: str,
    *,
    status: Literal["success", "failed"],
    result_summary: str | None,
    error: str | None,
    started_at: datetime,
    finished_at: datetime,
) -> None:
    await asyncio.to_thread(
        supabase_store.finish_run,
        user_id,
        run_id,
        status=status,
        result_summary=result_summary,
        error=error,
        started_at=started_at,
        finished_at=finished_at,
    )


async def set_automation_run_times(
    user_id: str,
    automation_id: str,
    *,
    last_run_at: datetime | None = None,
    next_run_at: datetime | None = None,
) -> None:
    await asyncio.to_thread(
        supabase_store.set_automation_run_times,
        user_id,
        automation_id,
        last_run_at=last_run_at,
        next_run_at=next_run_at,
    )


async def compute_next_cron_fire(
    cron_expression: str, tz_name: str, base: datetime | None = None
) -> datetime | None:
    from koraku.automations.cron_next import compute_next_cron_fire as _cn

    return await asyncio.to_thread(_cn, cron_expression, tz_name, base)
