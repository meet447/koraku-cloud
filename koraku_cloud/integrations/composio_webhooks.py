"""Composio project webhook subscription + inbound signature verification."""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from koraku.core.config import settings
from koraku.integrations import composio as composio_runtime

log = logging.getLogger(__name__)

_COMPOSIO_API_BASE = "https://backend.composio.dev/api/v3.1"
_TRIGGER_EVENTS_PATH = "/api/composio/trigger-events"


def composio_webhook_configured() -> bool:
    secret = (getattr(settings, "composio_webhook_secret", None) or "").strip()
    return composio_runtime.is_configured() and bool(secret)


def composio_trigger_events_url() -> str | None:
    base = (getattr(settings, "koraku_public_api_url", None) or "").strip().rstrip("/")
    if not base:
        return None
    return f"{base}{_TRIGGER_EVENTS_PATH}"


def ensure_project_webhook_subscription() -> None:
    """
    Register Koraku's public URL with Composio (once per deployment).

    Requires COMPOSIO_API_KEY, KORAKU_PUBLIC_API_URL, and COMPOSIO_WEBHOOK_SECRET.
    Set COMPOSIO_WEBHOOK_AUTO_SETUP=true to POST a subscription when none matches the URL.
    """
    if not composio_runtime.is_configured():
        return
    url = composio_trigger_events_url()
    if not url:
        log.info(
            "Composio trigger webhooks: set KORAKU_PUBLIC_API_URL to register subscription."
        )
        return
    secret = (getattr(settings, "composio_webhook_secret", None) or "").strip()
    if not secret:
        log.warning(
            "Composio trigger webhooks: set COMPOSIO_WEBHOOK_SECRET (from Composio dashboard "
            "or subscription create response) to verify inbound events."
        )
        return
    auto = (getattr(settings, "composio_webhook_auto_setup", None) or "").strip().lower()
    if auto not in ("1", "true", "yes", "on"):
        return
    api_key = composio_runtime.effective_api_key()
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}
    try:
        with httpx.Client(timeout=30.0) as client:
            list_r = client.get(
                f"{_COMPOSIO_API_BASE}/webhook_subscriptions",
                headers=headers,
            )
            if list_r.status_code < 400:
                data = list_r.json()
                items = data if isinstance(data, list) else data.get("items") or data.get("data") or []
                for row in items:
                    if not isinstance(row, dict):
                        continue
                    if (row.get("webhook_url") or "").rstrip("/") == url.rstrip("/"):
                        log.info("Composio webhook subscription already points at %s", url)
                        return
            body = {
                "webhook_url": url,
                "enabled_events": ["composio.trigger.message"],
                "version": "V3",
            }
            create_r = client.post(
                f"{_COMPOSIO_API_BASE}/webhook_subscriptions",
                headers=headers,
                content=json.dumps(body),
            )
            if create_r.status_code >= 400:
                log.warning(
                    "Composio webhook subscription create failed: %s %s",
                    create_r.status_code,
                    create_r.text[:500],
                )
                return
            log.info("Composio webhook subscription created for %s", url)
    except Exception:
        log.exception("Composio webhook subscription setup failed")


def verify_composio_trigger_webhook(
    *,
    webhook_id: str,
    payload: str,
    signature: str,
    timestamp: str,
) -> dict[str, Any]:
    """Verify and normalize a Composio V3 trigger webhook body."""
    secret = (getattr(settings, "composio_webhook_secret", None) or "").strip()
    if not secret:
        raise RuntimeError("COMPOSIO_WEBHOOK_SECRET is not set")
    from koraku.workspace.paths import workspace_dir

    composio_runtime.configure_workspace_cache(workspace_dir())
    c = composio_runtime._client()
    result = c.triggers.verify_webhook(
        id=webhook_id,
        payload=payload,
        secret=secret,
        signature=signature,
        timestamp=timestamp,
    )
    return dict(result)
