"""Redis via ``REDIS_URL`` (local or any TCP Redis). Used for sessions and rate limits."""
from __future__ import annotations

import logging
from typing import Any

from koraku.core.config import settings

log = logging.getLogger(__name__)

_client: Any | None = None
_client_checked = False


def redis_url() -> str:
    return (settings.redis_url or "").strip()


def is_configured() -> bool:
    return bool(redis_url())


def get_client() -> Any | None:
    """Return a shared ``redis.Redis`` client (decode_responses=True), or ``None`` if unavailable."""
    global _client, _client_checked
    if _client_checked:
        return _client
    _client_checked = True
    url = redis_url()
    if not url:
        return None
    try:
        import redis

        client = redis.Redis.from_url(url, decode_responses=True)
        client.ping()
        _client = client
    except Exception as e:
        log.warning("Redis unavailable (%s): %s", url, e)
        _client = None
    return _client


def reset_client() -> None:
    """Test helper — drop cached connection."""
    global _client, _client_checked
    _client = None
    _client_checked = False


def get(key: str) -> str | None:
    client = get_client()
    if client is None:
        return None
    try:
        return client.get(key)
    except Exception as e:
        log.warning("redis GET %s failed: %s", key, e)
        return None


def setex(key: str, value: str, ttl_seconds: int) -> bool:
    client = get_client()
    if client is None:
        return False
    try:
        client.set(key, value, ex=max(1, int(ttl_seconds)))
        return True
    except Exception as e:
        log.warning("redis SET %s failed: %s", key, e)
        return False


def delete(key: str) -> None:
    client = get_client()
    if client is None:
        return
    try:
        client.delete(key)
    except Exception as e:
        log.warning("redis DEL %s failed: %s", key, e)


def increment_with_ttl(key: str, ttl_seconds: int) -> int | None:
    """Atomically INCR and set TTL on first write (fixed-window rate limits)."""
    client = get_client()
    if client is None:
        return None
    try:
        pipe = client.pipeline()
        pipe.incr(key)
        pipe.expire(key, max(1, int(ttl_seconds)), nx=True)
        results = pipe.execute()
        return int(results[0])
    except Exception as e:
        log.warning("redis INCR %s failed: %s", key, e)
        return None
