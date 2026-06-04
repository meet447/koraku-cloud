"""Rate limit and idempotency helpers for inbound automation webhooks."""
from __future__ import annotations

import hashlib
import time
from typing import Any

from fastapi import HTTPException, Request

from koraku.core.rate_limit import RateLimit, enforce_rate_limit, rate_limit_key

_IDEMPOTENCY_TTL_SECONDS = 300.0
_IDEMPOTENCY_MAX_KEYS = 4096
_seen_idempotency: dict[str, float] = {}


def _prune_idempotency(now: float) -> None:
    expired = [k for k, exp in _seen_idempotency.items() if exp <= now]
    for k in expired:
        _seen_idempotency.pop(k, None)
    if len(_seen_idempotency) > _IDEMPOTENCY_MAX_KEYS:
        oldest = sorted(_seen_idempotency.items(), key=lambda x: x[1])[
            : len(_seen_idempotency) - _IDEMPOTENCY_MAX_KEYS
        ]
        for k, _ in oldest:
            _seen_idempotency.pop(k, None)


def idempotency_key(request: Request, automation_id: str, body: dict[str, Any]) -> str | None:
    """Build a stable dedupe key from headers or a hash of the JSON body."""
    for header in ("X-Idempotency-Key", "X-Webhook-Id", "Webhook-Id"):
        raw = (request.headers.get(header) or "").strip()
        if raw:
            return f"{automation_id}:{header}:{raw[:200]}"
    digest = hashlib.sha256(
        f"{automation_id}:{body!r}".encode("utf-8", errors="replace")
    ).hexdigest()[:32]
    return f"{automation_id}:body:{digest}"


def claim_idempotency(key: str) -> bool:
    """Return True when this key is new; False when a recent duplicate was seen."""
    now = time.monotonic()
    _prune_idempotency(now)
    exp = _seen_idempotency.get(key)
    if exp is not None and exp > now:
        return False
    _seen_idempotency[key] = now + _IDEMPOTENCY_TTL_SECONDS
    return True


def enforce_automation_webhook_rate_limit(request: Request, automation_id: str) -> None:
    """Per-IP + automation cap to limit abuse when a webhook token leaks."""
    enforce_rate_limit(
        RateLimit(
            key=f"{rate_limit_key(request, scope='automation-webhook', user_id=None)}:{automation_id}",
            limit=60,
            window_seconds=60.0,
        )
    )


def reject_duplicate_webhook() -> None:
    raise HTTPException(
        status_code=409,
        detail="Duplicate webhook delivery (idempotency window).",
    )
