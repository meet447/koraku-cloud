"""Send an interim outbound message on the active external channel (iMessage / SMS)."""
from __future__ import annotations

from koraku.channels.context import deliver_channel_message, get_active_channel
from koraku.tools.tool_def import Tool


async def _channel_send_handler(message: str) -> str:
    ch = get_active_channel()
    if ch is None:
        return "Error: ChannelSend is only available during an iMessage/SMS turn."
    body = (message or "").strip()
    if not body:
        return "Error: message must not be empty."
    if len(body) > 1200:
        body = body[:1197] + "…"
    ok = await deliver_channel_message(body)
    if not ok:
        return "Error: could not send channel message."
    return "Sent to user on iMessage."


CHANNEL_SEND_TOOL = Tool(
    name="ChannelSend",
    description=(
        "Send a **short** message to the user on iMessage/SMS **before** you finish the turn. "
        "Use 1–3 times per turn for natural pacing (e.g. 'Let me check your inbox.', then after tools "
        "a summary). Keep each message under ~400 characters. Plain text only — no markdown tables."
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
    handler=_channel_send_handler,
    categories=["channel"],
)
