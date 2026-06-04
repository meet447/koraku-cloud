"""Blaxel per-user ensure locks are bounded."""
from __future__ import annotations

import asyncio

from koraku.integrations import blaxel_lazy as bl


def test_ensure_locks_evict_oldest_when_over_cap(monkeypatch) -> None:
    monkeypatch.setattr(bl, "_ENSURE_LOCK_MAX", 3)
    bl._ensure_locks.clear()
    keys = ["user-a", "user-b", "user-c", "user-d"]
    for i, key in enumerate(keys):
        monkeypatch.setattr(bl, "effective_cloud_user_id", lambda k=key: k)
        bl._lock_for_user()
    assert len(bl._ensure_locks) == 3
    assert "user-a" not in bl._ensure_locks
    assert "user-d" in bl._ensure_locks
