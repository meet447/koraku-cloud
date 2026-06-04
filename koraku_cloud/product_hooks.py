"""Cloud product hooks registered into ``koraku.core.product_hooks`` at bootstrap."""
from __future__ import annotations

import asyncio
from typing import Any

from koraku.core.models import SessionState


async def hydrate_session_for_turn(
    session: SessionState,
    *,
    incoming_user_text: str,
    auth_sub: str | None,
    auth_org_id: str | None = None,
    client_history: list[dict[str, Any]] | None = None,
) -> Any:
    from koraku_cloud.integrations.supabase_chat_history import hydrate_session_messages_from_db

    return await hydrate_session_messages_from_db(
        session,
        incoming_user_text=incoming_user_text,
        auth_sub=auth_sub,
        auth_org_id=auth_org_id,
        client_history=client_history,
    )


async def fetch_account_personalization(
    auth_sub: str | None,
    auth_org_id: str | None,
) -> dict[str, str] | None:
    if not auth_sub:
        return None
    from koraku_cloud.integrations.supabase_personalization import fetch_personalization_async

    return await fetch_personalization_async(auth_sub, org_id=auth_org_id)


async def after_turn_memory_ingest(
    *,
    auth_sub: str | None,
    auth_org_id: str | None,
    msg: str,
    session: SessionState,
    run_id: str,
) -> None:
    if not auth_sub:
        return
    from koraku.integrations.supermemory_client import (
        extract_last_assistant_text,
        ingest_chat_turn_sync,
        supermemory_configured,
    )

    if not supermemory_configured():
        return
    assistant_text = extract_last_assistant_text(session)
    if not msg.strip() and not assistant_text:
        return
    await asyncio.to_thread(
        ingest_chat_turn_sync,
        auth_sub,
        user_text=msg.strip(),
        assistant_text=assistant_text,
        org_id=auth_org_id,
        session_id=session.session_id,
        run_id=run_id,
    )


def resolve_tenant_org(request: Any, sub: str) -> tuple[str | None, str | None]:
    from koraku.core.config import settings

    if (settings.auth_backend or "").strip().lower() != "supabase":
        return None, None
    from koraku_cloud.integrations.supabase_tenant import parse_org_header, resolve_org_id_sync

    return resolve_org_id_sync(sub, parse_org_header(request.headers))


def health_detail_extras() -> dict[str, object]:
    from koraku.core.config import settings
    from koraku.integrations.supermemory_client import supermemory_configured
    from koraku_cloud.automations import scheduler as automation_scheduler
    from koraku_cloud.automations.supabase_store import supabase_automations_configured
    from koraku_cloud.integrations.supabase_chat_history import supabase_chat_history_configured
    from koraku_cloud.integrations.supabase_personalization import (
        supabase_personalization_configured,
    )

    return {
        "automation_scheduler_running": automation_scheduler.is_running(),
        "automation_scheduler_leader": automation_scheduler.is_automation_scheduler_leader(),
        "automation_scheduler_enabled": settings.automation_scheduler_enabled,
        "automation_max_steps": settings.automation_max_steps,
        "automation_run_timeout_seconds": settings.automation_run_timeout_seconds,
        "automations_supabase_configured": supabase_automations_configured(),
        "chat_history_supabase_configured": supabase_chat_history_configured(),
        "personalization_supabase_configured": supabase_personalization_configured(),
        "supermemory_configured": supermemory_configured(),
    }


def extra_agent_tools() -> list[Any]:
    from koraku.core.config import settings
    from koraku_cloud.automations.agent_tools import build_automation_tools

    tools: list[Any] = list(build_automation_tools())
    if (
        settings.sendblue_api_key
        and settings.sendblue_api_secret
        and settings.sendblue_from_number
    ):
        from koraku_cloud.tools.imessage_send_tool import IMESSAGE_SEND_TOOL

        tools.append(IMESSAGE_SEND_TOOL)
    return tools
