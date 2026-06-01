"""Lazy Blaxel helpers."""

from __future__ import annotations

import pytest

from koraku.integrations import blaxel_lazy as bl


@pytest.mark.asyncio
async def test_warm_blaxel_session_background_noops_without_lazy_session(monkeypatch) -> None:
    called = {"n": 0}

    async def fake_ensure() -> bool:
        called["n"] += 1
        return True

    monkeypatch.setattr(bl, "ensure_blaxel_for_file_tool", fake_ensure)
    monkeypatch.setattr(bl, "cloud_blaxel_block_reason", lambda _s: None)
    await bl.warm_blaxel_session_background()
    assert called["n"] == 0


@pytest.mark.asyncio
async def test_warm_blaxel_session_background_uses_lazy_session(monkeypatch) -> None:
    called = {"n": 0}
    tok = bl.set_lazy_blaxel_session("sess-1")

    async def fake_ensure() -> bool:
        called["n"] += 1
        return True

    monkeypatch.setattr(bl, "ensure_blaxel_for_file_tool", fake_ensure)
    monkeypatch.setattr(bl, "cloud_blaxel_block_reason", lambda _s: None)
    try:
        await bl.warm_blaxel_session_background()
    finally:
        bl.clear_lazy_blaxel_session(tok)
    assert called["n"] == 1
