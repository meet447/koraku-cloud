"""Send automation run results to a user's linked iMessage number."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from koraku.integrations import sendblue_client
from koraku_cloud.integrations.supabase_external import (
    append_thread_message_sync,
    get_phone_link_for_user_sync,
)

log = logging.getLogger(__name__)

IMESSAGE_NOT_LINKED = (
    "iMessage is not linked. Open Koraku → External to link your phone before enabling iMessage delivery."
)
IMESSAGE_NOT_CONFIGURED = (
    "iMessage delivery is not available on this server (SendBlue is not configured)."
)


def user_imessage_phone_sync(user_id: str) -> str | None:
    link = get_phone_link_for_user_sync(user_id)
    if not link:
        return None
    phone = str(link.get("phone_e164") or "").strip()
    return phone or None


def assert_notify_via_imessage_allowed(user_id: str) -> None:
    """Raise ValueError when the user cannot enable iMessage delivery."""
    if not sendblue_client.configured():
        raise ValueError(IMESSAGE_NOT_CONFIGURED)
    if not user_imessage_phone_sync(user_id):
        raise ValueError(IMESSAGE_NOT_LINKED)


def imessage_delivery_status_sync(user_id: str) -> dict[str, bool]:
    linked = bool(user_imessage_phone_sync(user_id))
    return {
        "configured": sendblue_client.configured(),
        "linked": linked,
        "available": sendblue_client.configured() and linked,
    }


def format_automation_imessage_body(
    *,
    title: str,
    status: str,
    result_summary: str | None,
    error: str | None,
) -> str:
    name = (title or "Automation").strip() or "Automation"
    if status == "success":
        body = (result_summary or "").strip() or "Run finished successfully (no summary text)."
        return f"[Koraku] {name}\n\n{body}"
    err = (error or "Run failed.").strip()
    return f"[Koraku] {name}\n\nAutomation run failed.\n\n{err}"


async def send_automation_result_via_imessage(
    user_id: str,
    *,
    title: str,
    status: str,
    result_summary: str | None,
    error: str | None,
) -> bool:
    """Deliver automation outcome to the user's linked phone. Returns True if send was attempted and succeeded."""
    link = await asyncio.to_thread(get_phone_link_for_user_sync, user_id)
    if not link:
        log.warning("automation imessage notify skipped: no phone link user=%s", user_id[:8])
        return False
    phone = str(link.get("phone_e164") or "").strip()
    if not phone:
        return False
    if not sendblue_client.configured():
        log.warning("automation imessage notify skipped: sendblue not configured")
        return False

    text = format_automation_imessage_body(
        title=title,
        status=status,
        result_summary=result_summary,
        error=error,
    )
    ok = await sendblue_client.send_message(phone, text)
    thread_id = str(link.get("imessage_thread_id") or "").strip()
    if ok and thread_id:
        await asyncio.to_thread(
            append_thread_message_sync,
            thread_id=thread_id,
            role="assistant",
            text=text,
        )
    return ok
