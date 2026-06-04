"""Small in-process TTL cache for per-request Supabase / Supermemory lookups."""
from __future__ import annotations

import time
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class TtlCache(Generic[T]):
    """Thread-unsafe TTL map; fine for asyncio single-process API workers."""

    __slots__ = ("_data", "_max_size")

    def __init__(self, *, max_size: int = 512) -> None:
        self._data: dict[str, tuple[float, T]] = {}
        self._max_size = max(16, int(max_size))

    def get(self, key: str, *, ttl_seconds: float) -> T | None:
        k = (key or "").strip()
        if not k:
            return None
        row = self._data.get(k)
        if row is None:
            return None
        _ts, value = row
        ttl = float(ttl_seconds)
        # ttl_seconds <= 0: no expiry (invalidate explicitly via ``invalidate``).
        if ttl > 0 and (time.monotonic() - _ts) >= ttl:
            self._data.pop(k, None)
            return None
        return value

    def set(self, key: str, value: T) -> None:
        k = (key or "").strip()
        if not k:
            return
        if len(self._data) >= self._max_size:
            oldest = min(self._data.items(), key=lambda item: item[1][0])[0]
            self._data.pop(oldest, None)
        self._data[k] = (time.monotonic(), value)

    def invalidate(self, key: str) -> None:
        k = (key or "").strip()
        if k:
            self._data.pop(k, None)

    def clear(self) -> None:
        self._data.clear()


def cache_get_or_set(
    cache: TtlCache[T],
    key: str,
    *,
    ttl_seconds: float,
    loader: Any,
) -> T:
    """Return cached value or call ``loader()`` once and store the result."""
    hit = cache.get(key, ttl_seconds=ttl_seconds)
    if hit is not None:
        return hit
    value = loader()
    cache.set(key, value)
    return value
