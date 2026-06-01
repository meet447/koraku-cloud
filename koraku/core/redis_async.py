"""Async Redis client (``REDIS_URL``) for SSE pub/sub and detached runs."""
from __future__ import annotations

import logging
from typing import Any

from koraku.core.config import settings

log = logging.getLogger(__name__)

_client: Any | None = None
_client_checked = False


def is_configured() -> bool:
    return bool((settings.redis_url or "").strip())


async def get_client() -> Any | None:
    """Shared ``redis.asyncio.Redis`` (decode_responses=True), or ``None``."""
    global _client, _client_checked
    if _client_checked:
        return _client
    _client_checked = True
    url = (settings.redis_url or "").strip()
    if not url:
        return None
    try:
        from redis import asyncio as aioredis

        client = aioredis.from_url(url, decode_responses=True)
        await client.ping()
        _client = client
    except Exception as e:
        log.warning("Async Redis unavailable (%s): %s", url, e)
        _client = None
    return _client


def reset_client() -> None:
    global _client, _client_checked
    _client = None
    _client_checked = False
