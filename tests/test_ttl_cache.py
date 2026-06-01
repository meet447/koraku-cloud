"""TTL cache helpers."""

from __future__ import annotations

import time

from koraku.core.ttl_cache import TtlCache


def test_ttl_cache_hit_and_expiry() -> None:
    cache: TtlCache[str] = TtlCache(max_size=4)
    cache.set("a", "one")
    assert cache.get("a", ttl_seconds=60.0) == "one"
    cache._data["a"] = (time.monotonic() - 120.0, "one")
    assert cache.get("a", ttl_seconds=60.0) is None


def test_ttl_cache_invalidate() -> None:
    cache: TtlCache[str] = TtlCache(max_size=4)
    cache.set("user", "profile")
    cache.invalidate("user")
    assert cache.get("user", ttl_seconds=60.0) is None
