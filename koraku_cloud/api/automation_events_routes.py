"""Inbound webhooks for event-triggered automations."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from koraku_cloud.automations import async_ops
from koraku_cloud.automations.runner import queue_automation_run
from koraku_cloud.automations.webhook_tokens import verify_webhook_token

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/automation-events", tags=["automation-events"])


@router.post("/{automation_id}")
async def automation_event_webhook(
    automation_id: str,
    request: Request,
    token: str = Query(..., min_length=16),
) -> dict[str, Any]:
    """Trigger an event-mode automation (Bearer-less; use secret token query param)."""
    stored_hash = await async_ops.get_event_webhook_hash(automation_id)
    if not verify_webhook_token(token, stored_hash):
        raise HTTPException(status_code=401, detail="Invalid webhook token")

    auto = await async_ops.get_automation_for_event(automation_id)
    if auto is None:
        raise HTTPException(status_code=404, detail="Event automation not found")
    if auto.get("status") != "active":
        return {"ok": True, "skipped": True, "reason": "automation_paused"}

    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {"payload": body}

    payload_preview = json.dumps(body, default=str)[:2000]
    trigger_summary = f"Webhook event: {payload_preview}"

    agent = getattr(request.app.state, "koraku_agent", None)
    user_id = str(auto.get("user_id") or "")
    org_id = str(auto.get("org_id") or "")

    result = await queue_automation_run(
        user_id,
        automation_id,
        org_id=org_id,
        agent=agent,
        trigger_summary=trigger_summary,
    )
    return result
