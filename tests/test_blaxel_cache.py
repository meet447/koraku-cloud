"""Blaxel user sandbox cache helpers."""

from __future__ import annotations

import time

from koraku.core.config import settings
from koraku.integrations import blaxel_runtime as br


def test_user_sandbox_is_cached_respects_ttl(monkeypatch) -> None:
    br._sandbox_cache.clear()
    monkeypatch.setattr(br, "user_sandbox_name", lambda _uid: "koraku-user-test")
    monkeypatch.setattr(settings, "blaxel_sandbox_cache_ttl_seconds", 600.0)
    br._sandbox_cache["koraku-user-test"] = (object(), time.monotonic())
    assert br.user_sandbox_is_cached("user-1") is True
    br._sandbox_cache["koraku-user-test"] = (object(), time.monotonic() - 700.0)
    assert br.user_sandbox_is_cached("user-1") is False
