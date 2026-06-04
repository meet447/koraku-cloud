"""SDK session hydration — in-memory session, optional client history (no Supabase)."""
from __future__ import annotations

from typing import Any

from koraku.core.chat_history import ChatHistoryHydration, client_history_rows_to_agent_messages
from koraku.core.models import AgentMessage, SessionState


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


async def hydrate_sdk_session_for_turn(
    session: SessionState,
    *,
    incoming_user_text: str,
    auth_sub: str | None,
    auth_org_id: str | None = None,
    client_history: list[dict[str, Any]] | None = None,
) -> ChatHistoryHydration:
    """Load prior messages into ``session``; returns hydration trace object."""
    _ = incoming_user_text, auth_org_id
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
