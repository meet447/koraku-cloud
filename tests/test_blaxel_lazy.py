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
    sid_tok, _root_tok = bl.set_lazy_blaxel_session("sess-1")

    async def fake_ensure() -> bool:
        called["n"] += 1
        return True

    monkeypatch.setattr(bl, "ensure_blaxel_for_file_tool", fake_ensure)
    monkeypatch.setattr(bl, "cloud_blaxel_block_reason", lambda _s: None)
    try:
        await bl.warm_blaxel_session_background()
    finally:
        bl.clear_lazy_blaxel_session(sid_tok)
    assert called["n"] == 1


@pytest.mark.asyncio
async def test_lazy_ensure_uses_imessage_session_root_override(monkeypatch) -> None:
    import koraku.integrations.blaxel_lazy as bl
    from types import SimpleNamespace

    bound: list[str] = []

    class FakeSb:
        pass

    async def fake_ensure_session_workspace(sid: str, settings: object, *, user_id: str | None = None) -> tuple[FakeSb, str]:
        return FakeSb(), "/tmp/session-root"

    def fake_bind(sb: object, root: str) -> tuple[object, object]:
        bound.append(root)
        return (object(), object())

    monkeypatch.setattr(bl, "cloud_blaxel_block_reason", lambda _s: None)
    monkeypatch.setattr("koraku.integrations.blaxel_runtime.ensure_session_workspace", fake_ensure_session_workspace)
    monkeypatch.setattr(bl, "bind_blaxel_sandbox", fake_bind)
    monkeypatch.setattr(bl, "settings", SimpleNamespace(blaxel_cloud_sandbox_enabled=True, bl_workspace="ws", bl_api_key="key", blaxel_sandbox_image="", blaxel_sandbox_memory_mb=1024, blaxel_sandbox_cpu=1, blaxel_sandbox_region="us-east-1"))
    monkeypatch.setattr(bl, "effective_cloud_user_id", lambda: "user-1")

    imessage_root = "/tmp/koraku/users/user-1/imessage/thread-1"
    sid_tok, root_tok = bl.set_lazy_blaxel_session("web-session-id", session_root=imessage_root)
    try:
        ok = await bl.ensure_blaxel_for_file_tool()
    finally:
        bl.clear_lazy_blaxel_session(sid_tok, root_tok)
    assert ok is True
    assert bound == [imessage_root]
