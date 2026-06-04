"""Send outbound iMessage to the authenticated user's linked phone (SendBlue)."""
from __future__ import annotations

import asyncio
import logging
from contextvars import ContextVar, Token

from koraku.channels.context import get_active_channel
from koraku.integrations import sendblue_client
from koraku.integrations.cloud_user import effective_auth_user_sub
from koraku.tools.tool_def import Tool
from koraku_cloud.integrations.supabase_external import (
    append_thread_message_sync,
    get_phone_link_for_user_sync,
)

log = logging.getLogger(__name__)

MAX_IMESSAGE_SENDS_PER_RUN = 5
_MAX_CHARS = 1200

_send_count: ContextVar[int] = ContextVar("koraku_imessage_send_count", default=0)


def reset_imessage_send_budget() -> Token[int]:
    return _send_count.set(0)


def restore_imessage_send_budget(token: Token[int]) -> None:
    _send_count.reset(token)


async def _imessage_send_handler(message: str) -> str:
    ch = get_active_channel()
    if ch is not None:
        return (
            "Error: During a live iMessage chat, use ChannelSend instead of IMessageSend."
        )

    uid = (effective_auth_user_sub() or "").strip()
    if not uid:
        return "Error: No authenticated user — cannot send iMessage."

    if not sendblue_client.configured():
        return "Error: iMessage (SendBlue) is not configured on this server."

    body = (message or "").strip()
    if not body:
        return "Error: message must not be empty."
    if len(body) > _MAX_CHARS:
        body = body[: _MAX_CHARS - 1] + "…"

    n = _send_count.get()
    if n >= MAX_IMESSAGE_SENDS_PER_RUN:
        return f"Error: iMessage send limit reached for this run (max {MAX_IMESSAGE_SENDS_PER_RUN})."
    _send_count.set(n + 1)

    link = await asyncio.to_thread(get_phone_link_for_user_sync, uid)
    if not link:
        return (
            "Error: iMessage is not linked. The user must link their phone in Koraku → External."
        )
    phone = str(link.get("phone_e164") or "").strip()
    if not phone:
        return (
            "Error: iMessage is not linked. The user must link their phone in Koraku → External."
        )

    ok = await sendblue_client.send_message(phone, body)
    if not ok:
        return "Error: SendBlue could not deliver the message (check server logs)."

    thread_id = str(link.get("imessage_thread_id") or "").strip()
    if thread_id:
        await asyncio.to_thread(
            append_thread_message_sync,
            thread_id=thread_id,
            role="assistant",
            text=body,
        )
    log.info("imessage_send ok user=%s chars=%s", uid[:8], len(body))
    return "Sent to the user's linked iMessage."


IMESSAGE_SEND_TOOL = Tool(
    name="IMessageSend",
    description=(
        "Send a plain-text message to the user's linked iPhone/iMessage (requires phone linked "
        "in External). Use for short alerts or summaries during automations or chat — not for "
        "long reports. Keep under ~400 characters when possible; hard max ~1200. Up to 5 sends "
        "per agent run. During a live iMessage conversation, use ChannelSend instead."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Plain-text bubble to send now.",
            },
        },
        "required": ["message"],
    },
    handler=_imessage_send_handler,
    categories=["channel", "automations"],
)
