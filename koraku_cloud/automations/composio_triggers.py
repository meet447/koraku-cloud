"""Composio trigger instances wired to Koraku event automations."""
from __future__ import annotations

import json
import logging
from typing import Any

from koraku.integrations import composio as composio_runtime
from koraku.workspace.paths import workspace_dir

log = logging.getLogger(__name__)

# MVP allowlist — expand as we validate more trigger types in production.
ALLOWED_COMPOSIO_TRIGGER_SLUGS: frozenset[str] = frozenset({
    "GMAIL_NEW_GMAIL_MESSAGE",
})

_TRIGGER_LABELS: dict[str, str] = {
    "GMAIL_NEW_GMAIL_MESSAGE": "New Gmail message",
}

_TOOLKIT_FOR_SLUG: dict[str, str] = {
    "GMAIL_NEW_GMAIL_MESSAGE": "GMAIL",
}


def validate_composio_trigger_slug(slug: str) -> str:
    s = (slug or "").strip().upper()
    if s not in ALLOWED_COMPOSIO_TRIGGER_SLUGS:
        allowed = ", ".join(sorted(ALLOWED_COMPOSIO_TRIGGER_SLUGS))
        raise ValueError(f"Unsupported Composio trigger. Allowed: {allowed}")
    return s


def trigger_display_label(slug: str) -> str:
    s = (slug or "").strip().upper()
    return _TRIGGER_LABELS.get(s, s.replace("_", " ").title())


def toolkit_for_trigger_slug(slug: str) -> str:
    s = (slug or "").strip().upper()
    tk = _TOOLKIT_FOR_SLUG.get(s)
    if not tk and "_" in s:
        tk = s.split("_", 1)[0]
    return tk or s


def _bind_user(user_id: str) -> Any:
    composio_runtime.configure_workspace_cache(workspace_dir())
    tok = composio_runtime.set_composio_request_user(user_id)
    if tok is None:
        raise RuntimeError("user_id is required for Composio triggers")
    return tok


def create_trigger_instance(*, user_id: str, trigger_slug: str) -> str:
    """Create a Composio trigger for the user's connected account; returns trigger_id."""
    slug = validate_composio_trigger_slug(trigger_slug)
    tk = toolkit_for_trigger_slug(slug)
    active = set(composio_runtime.active_toolkit_slugs())
    if tk not in active:
        raise ValueError(
            f"Connect {tk} in Connections before using trigger {slug}."
        )
    tok = _bind_user(user_id)
    try:
        c = composio_runtime._client()
        resp = c.triggers.create(slug=slug, user_id=user_id)
        tid = (getattr(resp, "trigger_id", None) or "").strip()
        if not tid:
            raise RuntimeError("Composio did not return a trigger_id")
        return tid
    finally:
        composio_runtime.reset_composio_request_user(tok)


def set_trigger_enabled(*, trigger_id: str, enabled: bool) -> None:
    if not (trigger_id or "").strip():
        return
    composio_runtime.configure_workspace_cache(workspace_dir())
    c = composio_runtime._client()
    if enabled:
        c.triggers.enable(trigger_id=trigger_id.strip())
    else:
        c.triggers.disable(trigger_id=trigger_id.strip())


def delete_trigger_instance(trigger_id: str) -> None:
    tid = (trigger_id or "").strip()
    if not tid:
        return
    composio_runtime.configure_workspace_cache(workspace_dir())
    c = composio_runtime._client()
    try:
        c.triggers.delete(trigger_id=tid)
    except Exception:
        log.exception("Composio trigger delete failed trigger_id=%s", tid)


def list_trigger_options_for_user(user_id: str) -> list[dict[str, Any]]:
    """Catalog entries the user can attach to an automation (connected toolkits only)."""
    if not composio_runtime.is_configured():
        return []
    tok = _bind_user(user_id)
    try:
        active = set(composio_runtime.active_toolkit_slugs())
    finally:
        composio_runtime.reset_composio_request_user(tok)
    out: list[dict[str, Any]] = []
    for slug in sorted(ALLOWED_COMPOSIO_TRIGGER_SLUGS):
        tk = toolkit_for_trigger_slug(slug)
        if tk not in active:
            continue
        out.append({
            "slug": slug,
            "label": trigger_display_label(slug),
            "toolkit": tk,
            "polling": slug.startswith("GMAIL"),
            "description": (
                "Composio polls Gmail periodically; delivery may lag by several minutes."
                if slug.startswith("GMAIL")
                else "Realtime when the provider supports webhooks."
            ),
        })
    return out


def format_composio_trigger_summary(event: dict[str, Any]) -> str:
    slug = str(event.get("trigger_slug") or "")
    payload = event.get("payload")
    if not isinstance(payload, dict):
        payload = {}
    if "GMAIL" in slug.upper():
        subject = payload.get("subject") or payload.get("snippet") or "(no subject)"
        sender = payload.get("from") or payload.get("sender") or "unknown"
        return (
            f"Composio trigger ({slug}): new email — subject={subject!s}, from={sender!s}"
        )[:2000]
    preview = json.dumps(payload, default=str)[:1800]
    return f"Composio trigger ({slug}): {preview}"[:2000]
