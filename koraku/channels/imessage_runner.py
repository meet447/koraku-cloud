"""Run Koraku agent for an inbound SendBlue / iMessage message."""
from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

from koraku.agent import Agent
from koraku.agent.context_manager import ContextManager
from koraku.agent.sessions import get_or_create_chat_session
from koraku.channels.context import ActiveChannel, reset_active_channel, set_active_channel
from koraku.channels.imessage_prompt import imessage_system_appendix
from koraku.core.config import settings
from koraku.integrations import composio as composio_runtime
from koraku.integrations.cloud_user import reset_cloud_user_id, set_cloud_user_id
from koraku.integrations import sendblue_client
from koraku.integrations.sendblue_client import send_message
from koraku.integrations.supabase_chat_history import hydrate_session_messages_from_db
from koraku.integrations.supabase_external import append_thread_message_sync, lookup_user_by_phone_sync
from koraku.core.tenant import reset_tenant_org_id, set_tenant_org_id
from koraku.agent.runtime_context import AgentRunContext
from koraku.tools.channel_send_tool import CHANNEL_SEND_TOOL

log = logging.getLogger(__name__)

_dedup_handles: dict[str, float] = {}
_DEDUP_TTL_SEC = 3600.0


def claim_message_handle(handle: str) -> bool:
    import time

    if not handle:
        return True
    now = time.monotonic()
    stale = [k for k, t in _dedup_handles.items() if now - t > _DEDUP_TTL_SEC]
    for k in stale:
        _dedup_handles.pop(k, None)
    if handle in _dedup_handles:
        return False
    _dedup_handles[handle] = now
    return True


async def run_imessage_turn(
    *,
    agent: Agent,
    phone_e164: str,
    text: str,
    link: dict[str, Any],
) -> None:
    user_id = str(link.get("user_id") or "")
    org_id = str(link.get("org_id") or "")
    thread_id = str(link.get("imessage_thread_id") or "")
    if not user_id or not thread_id:
        return

    stop_typing = asyncio.Event()

    async def _typing_task() -> None:
        await sendblue_client.send_typing_indicator(phone_e164)
        while not stop_typing.is_set():
            try:
                await asyncio.wait_for(stop_typing.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                await sendblue_client.send_typing_indicator(phone_e164)

    typing_task = asyncio.create_task(_typing_task())

    sent_parts: list[str] = []

    async def on_send(msg: str) -> None:
        body = (msg or "").strip()
        if not body:
            return
        await send_message(phone_e164, body)
        sent_parts.append(body)
        await asyncio.to_thread(
            append_thread_message_sync,
            thread_id=thread_id,
            role="assistant",
            text=body,
        )

    channel = ActiveChannel(
        kind="imessage",
        outbound_phone=phone_e164,
        thread_id=thread_id,
        user_id=user_id,
        org_id=org_id,
    )
    t_ch, t_send = set_active_channel(channel, on_send=on_send)
    composio_tok = composio_runtime.set_composio_request_user(user_id)
    cloud_tok = set_cloud_user_id(user_id)
    tenant_tok = set_tenant_org_id(org_id)

    imessage_cm = ContextManager(summarize_after=10, max_tool_result_chars=2000)
    prev_cm = agent.context_manager
    agent.context_manager = imessage_cm

    try:
        session = get_or_create_chat_session(
            thread_id,
            owner_sub=user_id,
            owner_org_id=org_id,
        )
        await hydrate_session_messages_from_db(
            session,
            incoming_user_text=text.strip(),
            auth_sub=user_id,
            auth_org_id=org_id,
            client_history=[],
        )
        await asyncio.to_thread(
            append_thread_message_sync,
            thread_id=thread_id,
            role="user",
            text=text.strip(),
        )

        def emit(_ev: dict[str, Any]) -> None:
            return

        run_context = AgentRunContext(
            execution_target="cloud",
            extra_tools=(CHANNEL_SEND_TOOL,),
            system_appendix=imessage_system_appendix(),
        )
        async for _ in agent.run(
            text.strip(),
            session,
            emit,
            run_context=run_context,
        ):
            pass

        final = ""
        for m in reversed(session.messages):
            if m.role == "assistant" and isinstance(m.content, str) and m.content.strip():
                final = m.content.strip()
                break

        if final:
            tail = final
            for part in sent_parts:
                if tail.startswith(part):
                    tail = tail[len(part) :].lstrip()
            if tail.strip() and tail.strip() not in sent_parts:
                await on_send(tail)
    except Exception:
        log.exception("imessage agent turn failed")
        await send_message(
            phone_e164,
            "Something went wrong on my side — try again in a moment.",
        )
    finally:
        agent.context_manager = prev_cm
        reset_active_channel(t_ch, t_send)
        if composio_tok is not None:
            composio_runtime.reset_composio_request_user(composio_tok)
        if cloud_tok is not None:
            reset_cloud_user_id(cloud_tok)
        if tenant_tok is not None:
            reset_tenant_org_id(tenant_tok)
        stop_typing.set()
        typing_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await typing_task
