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
from koraku.channels.file_attachments import (
    end_imessage_file_capture,
    send_queued_imessage_attachments,
    start_imessage_file_capture,
)
from koraku.channels.imessage_progress import make_imessage_emit
from koraku.channels.imessage_prompt import imessage_system_appendix
from koraku.channels.imessage_sandbox import (
    imessage_blaxel_available,
    imessage_workspace_root,
    prepare_imessage_sandbox,
)
from koraku.core.config import settings
from koraku.integrations import composio as composio_runtime
from koraku.integrations.cloud_user import reset_cloud_user_id, set_cloud_user_id
from koraku.integrations.blaxel_lazy import clear_lazy_blaxel_session, set_lazy_blaxel_session
from koraku.integrations import sendblue_client
from koraku.integrations.sendblue_client import send_message
from koraku.integrations.supermemory_client import extract_last_assistant_text
from koraku.core.tenant import reset_tenant_org_id, set_tenant_org_id
from koraku.agent.runtime_context import AgentRunContext
from koraku.tools.channel_send_tool import CHANNEL_SEND_TOOL

log = logging.getLogger(__name__)


async def _hydrate_session_messages_from_db(*args: Any, **kwargs: Any) -> None:
    try:
        from koraku_cloud.integrations.supabase_chat_history import (
            hydrate_session_messages_from_db,
        )
    except ImportError:
        return
    await hydrate_session_messages_from_db(*args, **kwargs)


def _append_thread_message_sync(*args: Any, **kwargs: Any) -> None:
    try:
        from koraku_cloud.integrations.supabase_external import append_thread_message_sync
    except ImportError:
        return
    append_thread_message_sync(*args, **kwargs)


_dedup_handles: dict[str, float] = {}
_DEDUP_TTL_SEC = 3600.0


def claim_message_handle(handle: str) -> bool:
    """Return True when this handle should be processed (first claim wins)."""
    import time

    from koraku.core import redis_client

    if not handle:
        return True
    h = handle.strip()
    if not h:
        return True

    rkey = f"koraku:imessage:dedup:{h}"
    if redis_client.is_configured():
        claimed = redis_client.set_nx(rkey, "1", int(_DEDUP_TTL_SEC))
        if claimed is not None:
            return claimed

    now = time.monotonic()
    stale = [k for k, t in _dedup_handles.items() if now - t > _DEDUP_TTL_SEC]
    for k in stale:
        _dedup_handles.pop(k, None)
    if h in _dedup_handles:
        return False
    _dedup_handles[h] = now
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
    typing_task: asyncio.Task[None] | None = None

    async def _cancel_typing_task() -> None:
        nonlocal typing_task
        if typing_task is not None and not typing_task.done():
            typing_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await typing_task
        typing_task = None

    async def _halt_typing() -> None:
        """Stop typing for the rest of this turn."""
        if stop_typing.is_set():
            return
        stop_typing.set()
        await _cancel_typing_task()

    async def _pause_typing_for_bubble() -> None:
        """Pause refresh before an outbound bubble (iMessage lingers ~3s per ping)."""
        await _cancel_typing_task()

    async def _resume_typing() -> None:
        """Resume typing while the agent is still working after a bubble."""
        nonlocal typing_task
        if stop_typing.is_set():
            return
        if typing_task is not None and not typing_task.done():
            return
        typing_task = asyncio.create_task(_typing_task())

    async def _typing_task() -> None:
        await sendblue_client.send_typing_indicator(phone_e164)
        while not stop_typing.is_set():
            try:
                await asyncio.wait_for(stop_typing.wait(), timeout=4.0)
            except asyncio.TimeoutError:
                if stop_typing.is_set():
                    return
                await sendblue_client.send_typing_indicator(phone_e164)

    typing_task = asyncio.create_task(_typing_task())

    sent_parts: list[str] = []

    async def on_send(msg: str) -> None:
        body = (msg or "").strip()
        if not body:
            return
        await _pause_typing_for_bubble()
        await send_message(phone_e164, body)
        sent_parts.append(body)
        await asyncio.to_thread(
            _append_thread_message_sync,
            thread_id=thread_id,
            role="assistant",
            text=body,
        )
        await _resume_typing()

    channel = ActiveChannel(
        kind="imessage",
        outbound_phone=phone_e164,
        thread_id=thread_id,
        user_id=user_id,
        org_id=org_id,
    )
    t_ch, t_send = set_active_channel(channel, on_send=on_send)
    file_cap_tok = start_imessage_file_capture()
    composio_tok = composio_runtime.set_composio_request_user(user_id)
    cloud_tok = set_cloud_user_id(user_id)
    tenant_tok = set_tenant_org_id(org_id)

    imessage_cm = ContextManager(summarize_after=10, max_tool_result_chars=2000)
    prev_cm = agent.context_manager
    agent.context_manager = imessage_cm

    lazy_sid_tok = None
    lazy_root_tok = None
    cloud_sandbox = None
    imessage_root: str | None = None
    blaxel_on = imessage_blaxel_available()

    try:
        session = await asyncio.to_thread(
            get_or_create_chat_session,
            thread_id,
            owner_sub=user_id,
            owner_org_id=org_id,
        )
        from koraku.core.product_hooks import fetch_account_personalization

        account_p = None
        if user_id:
            try:
                account_p = await fetch_account_personalization(user_id, org_id)
            except Exception as e:
                log.warning("imessage personalization fetch failed: %s", e)

        if blaxel_on:
            cloud_sandbox, imessage_root = await prepare_imessage_sandbox(user_id, thread_id)
            if not imessage_root:
                imessage_root = imessage_workspace_root(user_id, thread_id)
            lazy_sid_tok, lazy_root_tok = set_lazy_blaxel_session(
                session.session_id,
                session_root=imessage_root,
            )
            if cloud_sandbox is None:
                log.warning(
                    "imessage turn deferred sandbox attach thread=%s root=%s",
                    thread_id[:12],
                    imessage_root,
                )
        await _hydrate_session_messages_from_db(
            session,
            incoming_user_text=text.strip(),
            auth_sub=user_id,
            auth_org_id=org_id,
            client_history=[],
        )
        await asyncio.to_thread(
            _append_thread_message_sync,
            thread_id=thread_id,
            role="user",
            text=text.strip(),
        )

        emit, drain_progress = make_imessage_emit(on_send)

        run_context = AgentRunContext(
            execution_target="cloud",
            extra_tools=(CHANNEL_SEND_TOOL,),
            system_appendix=imessage_system_appendix(imessage_root),
            blaxel_session_root=imessage_root,
        )
        async for _ in agent.run(
            text.strip(),
            session,
            emit,
            run_context=run_context,
            cloud_sandbox=cloud_sandbox,
            account_personalization=account_p,
        ):
            pass

        await drain_progress()
        await _halt_typing()

        final = extract_last_assistant_text(session)

        if final:
            tail = final
            for part in sent_parts:
                if tail.startswith(part):
                    tail = tail[len(part) :].lstrip()
            if tail.strip() and tail.strip() not in sent_parts:
                await _pause_typing_for_bubble()
                await send_message(phone_e164, tail)
                sent_parts.append(tail)
                await asyncio.to_thread(
                    _append_thread_message_sync,
                    thread_id=thread_id,
                    role="assistant",
                    text=tail,
                )

        if not sent_parts and not final.strip():
            log.warning("imessage turn produced no outbound text for thread %s", thread_id)
            await send_message(
                phone_e164,
                "I finished but had nothing to send — try asking again in one short sentence.",
            )
        else:
            log.info(
                "imessage turn done thread=%s bubbles=%s final_chars=%s",
                thread_id,
                len(sent_parts),
                len(final),
            )
    except Exception:
        log.exception("imessage agent turn failed")
        await _halt_typing()
        await send_message(
            phone_e164,
            "Something went wrong on my side — try again in a moment.",
        )
    finally:
        clear_lazy_blaxel_session(lazy_sid_tok, lazy_root_tok)
        agent.context_manager = prev_cm
        with contextlib.suppress(Exception):
            await send_queued_imessage_attachments(phone_e164)
        end_imessage_file_capture(file_cap_tok)
        reset_active_channel(t_ch, t_send)
        if composio_tok is not None:
            composio_runtime.reset_composio_request_user(composio_tok)
        if cloud_tok is not None:
            reset_cloud_user_id(cloud_tok)
        if tenant_tok is not None:
            reset_tenant_org_id(tenant_tok)
        await _halt_typing()
