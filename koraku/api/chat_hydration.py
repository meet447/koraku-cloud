"""Chat session hydration — SDK (in-memory / client) vs Cloud (Supabase)."""
from __future__ import annotations

import asyncio
from typing import Any

from koraku.core.chat_history import ChatHistoryHydration, client_history_rows_to_agent_messages
from koraku.core.models import AgentMessage, SessionState
from koraku.profiles import is_cloud_profile


def _cloud_authed(auth_sub: str | None) -> bool:
    return is_cloud_profile() and bool(auth_sub)


def _sdk_hydration(
    session: SessionState,
    *,
    source: str,
    reason: str,
    messages_before: int,
    messages_loaded: int,
    auth_sub: str | None = None,
    rows_fetched: int = 0,
) -> ChatHistoryHydration:
    return ChatHistoryHydration(
        session_id=session.session_id,
        source=source,
        reason=reason,
        auth_present=bool(auth_sub),
        supabase_configured=False,
        rows_fetched=rows_fetched,
        messages_loaded=messages_loaded,
        messages_before=messages_before,
    )


def _client_history_to_messages(client_history: list[dict[str, Any]] | None) -> list[AgentMessage]:
    if not client_history:
        return []
    return client_history_rows_to_agent_messages(client_history)


async def hydrate_session_for_turn(
    session: SessionState,
    *,
    incoming_user_text: str,
    auth_sub: str | None,
    auth_org_id: str | None = None,
    client_history: list[dict[str, Any]] | None = None,
) -> Any:
    """Load prior messages into ``session``; returns hydration trace object."""
    if is_cloud_profile():
        from koraku_cloud.integrations.supabase_chat_history import hydrate_session_messages_from_db

        return await hydrate_session_messages_from_db(
            session,
            incoming_user_text=incoming_user_text,
            auth_sub=auth_sub,
            auth_org_id=auth_org_id,
            client_history=client_history,
        )

    messages_before = len(session.messages)
    if messages_before > 0:
        return _sdk_hydration(
            session,
            source="session",
            reason="warm",
            messages_before=messages_before,
            messages_loaded=messages_before,
            auth_sub=auth_sub,
        )

    fallback = _client_history_to_messages(client_history)
    if fallback:
        session.messages = fallback
        session.touch()
        return _sdk_hydration(
            session,
            source="client",
            reason="sdk_client_history",
            messages_before=messages_before,
            messages_loaded=len(fallback),
            auth_sub=auth_sub,
        )

    return _sdk_hydration(
        session,
        source="memory",
        reason="sdk_empty",
        messages_before=messages_before,
        messages_loaded=messages_before,
        auth_sub=auth_sub,
    )


async def fetch_account_personalization(
    auth_sub: str | None,
    auth_org_id: str | None,
) -> dict[str, str] | None:
    """Cloud: Supabase personalization. SDK: none (use workspace ``.koraku/`` files)."""
    if not _cloud_authed(auth_sub):
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
    """Cloud optional Supermemory ingest after a chat turn."""
    if not _cloud_authed(auth_sub):
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
