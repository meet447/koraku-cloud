"""SendBlue inbound webhooks and external-channel helpers."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from koraku.channels.imessage_runner import claim_message_handle, run_imessage_turn
from koraku.channels.inbound_media import build_imessage_user_text
from koraku.core.config import settings
from koraku.core.request_auth import resolve_request_auth
from koraku.integrations import sendblue_client
from koraku_cloud.integrations.supabase_external import (
    confirm_verification_sync,
    lookup_user_by_phone_sync,
    start_verification_sync,
    try_confirm_from_inbound_message_sync,
)
from koraku.integrations.sendblue_client import configured as sendblue_configured

log = logging.getLogger(__name__)

router = APIRouter(prefix="/sendblue", tags=["sendblue"])


class VerifyStartBody(BaseModel):
    phone: str = Field(..., max_length=32)


class VerifyConfirmBody(BaseModel):
    phone: str = Field(..., max_length=32)
    code: str = Field(..., max_length=16)


def _agent(request: Request):
    return getattr(request.app.state, "koraku_agent", None)


@router.post("/webhook")
async def sendblue_webhook(request: Request) -> dict[str, Any]:
    if not sendblue_configured():
        raise HTTPException(status_code=503, detail="SendBlue is not configured")
    raw_headers = {k: v for k, v in request.headers.items()}
    if not sendblue_client.verify_webhook_secret(raw_headers):
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid JSON") from e
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object")

    content = body.get("content")
    is_outbound = bool(body.get("is_outbound"))
    from_number = sendblue_client.resolve_inbound_sender(body)
    message_handle = str(body.get("message_handle") or "")

    media_urls: list[str] = []
    raw_list = body.get("media_urls")
    if isinstance(raw_list, list):
        media_urls = [str(u) for u in raw_list if u]
    elif body.get("media_url"):
        media_urls = [str(body.get("media_url"))]

    if is_outbound or not from_number:
        return {"ok": True, "skipped": True}

    log.info("sendblue inbound from %s", from_number)
    text = content if isinstance(content, str) else ""
    if not text.strip() and not media_urls:
        return {"ok": True, "skipped": True}

    if message_handle and not claim_message_handle(message_handle):
        return {"ok": True, "deduped": True}

    agent = _agent(request)
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent unavailable")

    async def _process() -> None:
        try:
            text_use = await build_imessage_user_text(text=text, media_urls=media_urls)
            if not text_use.strip():
                return

            linked = await asyncio.to_thread(lookup_user_by_phone_sync, str(from_number))
            if linked:
                log.info("sendblue inbound linked user %s", linked.get("user_id"))
            elif text.strip():
                log.info("sendblue inbound: no koraku_phone_link for %s", from_number)
            if not linked:
                linked = await asyncio.to_thread(
                    try_confirm_from_inbound_message_sync,
                    phone_e164=str(from_number),
                    body=text_use.strip(),
                )
                if linked:
                    await sendblue_client.send_message(
                        str(from_number),
                        "You're verified — text me anytime.",
                    )
                    return
            if not linked:
                line = (settings.sendblue_from_number or "").strip()
                hint = (
                    f"Link this number in Koraku → External, or reply with your 6-digit code."
                )
                if line:
                    hint = f"Open Koraku → External to link your phone. Koraku line: {line}. {hint}"
                await sendblue_client.send_message(str(from_number), hint)
                return
            await run_imessage_turn(
                agent=agent,
                phone_e164=str(from_number),
                text=text_use,
                link=linked,
            )
        except Exception:
            log.exception("sendblue inbound processing failed")

    asyncio.create_task(_process())
    return {"ok": True}


@router.get("/status")
async def sendblue_status() -> dict[str, Any]:
    return {
        "configured": sendblue_configured(),
        "from_number": (settings.sendblue_from_number or "").strip() or None,
    }


@router.post("/verify/start")
async def verify_start(request: Request, body: VerifyStartBody) -> dict[str, Any]:
    if not sendblue_configured():
        raise HTTPException(status_code=503, detail="SendBlue is not configured")
    resolved = resolve_request_auth(request)
    if not resolved.sub:
        raise HTTPException(status_code=401, detail="Unauthorized")
    code = await asyncio.to_thread(
        start_verification_sync, user_id=str(resolved.sub), phone_e164=body.phone
    )
    msg = f"Your Koraku verification code is {code}. Enter it in the app under External, or reply KORAKU-{code} to this number."
    sent = await sendblue_client.send_message(body.phone, msg)
    return {"ok": True, "sent": sent}


@router.post("/verify/confirm")
async def verify_confirm(request: Request, body: VerifyConfirmBody) -> dict[str, Any]:
    resolved = resolve_request_auth(request)
    if not resolved.sub:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        thread_id = await asyncio.to_thread(
            confirm_verification_sync,
            user_id=str(resolved.sub),
            phone_e164=body.phone,
            code=body.code.strip(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True, "imessage_thread_id": thread_id}
