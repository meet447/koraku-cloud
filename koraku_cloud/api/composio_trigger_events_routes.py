"""Inbound Composio trigger webhooks → Koraku automations."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from koraku_cloud.automations import async_ops
from koraku_cloud.automations.composio_triggers import format_composio_trigger_summary
from koraku_cloud.automations.runner import queue_automation_run
from koraku_cloud.integrations.composio_webhooks import (
    composio_webhook_configured,
    verify_composio_trigger_webhook,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/composio", tags=["composio-triggers"])


@router.post("/trigger-events")
async def composio_trigger_events(request: Request) -> JSONResponse:
    """Receive Composio ``composio.trigger.message`` events (project webhook subscription)."""
    if not composio_webhook_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Composio trigger webhooks require COMPOSIO_API_KEY, "
                "COMPOSIO_WEBHOOK_SECRET, and KORAKU_PUBLIC_API_URL."
            ),
        )
    body = (await request.body()).decode("utf-8", errors="replace")
    webhook_id = (request.headers.get("webhook-id") or "").strip()
    signature = (request.headers.get("webhook-signature") or "").strip()
    timestamp = (request.headers.get("webhook-timestamp") or "").strip()
    if not webhook_id or not signature or not timestamp:
        raise HTTPException(status_code=400, detail="Missing Composio webhook headers")

    try:
        verified = verify_composio_trigger_webhook(
            webhook_id=webhook_id,
            payload=body,
            signature=signature,
            timestamp=timestamp,
        )
    except Exception as e:
        log.warning("Composio webhook verification failed: %s", e)
        raise HTTPException(status_code=401, detail="Invalid Composio webhook signature") from e

    raw = verified.get("raw_payload")
    if isinstance(raw, dict):
        event_type = str(raw.get("type") or "")
        if event_type and event_type != "composio.trigger.message":
            return JSONResponse({"ok": True, "skipped": True, "reason": event_type})

    event = verified.get("payload")
    if not isinstance(event, dict):
        return JSONResponse({"ok": True, "skipped": True, "reason": "no_payload"})

    trigger_id = str(event.get("id") or "").strip()
    meta = event.get("metadata")
    if not trigger_id and isinstance(meta, dict):
        trigger_id = str(
            meta.get("id") or meta.get("uuid") or meta.get("trigger_id") or ""
        ).strip()
    if not trigger_id:
        return JSONResponse({"ok": True, "skipped": True, "reason": "no_trigger_id"})

    automations = await async_ops.list_automations_by_composio_trigger_id(trigger_id)
    if not automations:
        return JSONResponse({"ok": True, "skipped": True, "reason": "no_matching_automation"})

    summary = format_composio_trigger_summary(event)
    agent = getattr(request.app.state, "koraku_agent", None)
    results: list[dict[str, Any]] = []
    for auto in automations:
        user_id = str(auto.get("user_id") or "")
        org_id = str(auto.get("org_id") or "")
        aid = str(auto.get("id") or "")
        if not user_id or not org_id or not aid:
            continue
        try:
            result = await queue_automation_run(
                user_id,
                aid,
                org_id=org_id,
                agent=agent,
                trigger_summary=summary,
            )
            results.append({"automation_id": aid, **result})
        except Exception:
            log.exception("Composio trigger queue failed automation_id=%s", aid)
            results.append({"automation_id": aid, "ok": False, "error": "queue_failed"})

    return JSONResponse({"ok": True, "trigger_id": trigger_id, "runs": results})
