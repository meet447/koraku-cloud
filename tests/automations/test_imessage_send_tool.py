import pytest

from koraku_cloud.tools.imessage_send_tool import (
    MAX_IMESSAGE_SENDS_PER_RUN,
    _imessage_send_handler,
    reset_imessage_send_budget,
)


@pytest.mark.asyncio
async def test_imessage_send_requires_auth(monkeypatch):
    monkeypatch.setattr(
        "koraku_cloud.tools.imessage_send_tool.effective_auth_user_sub",
        lambda: "",
    )
    out = await _imessage_send_handler("hello")
    assert "authenticated" in out.lower()


@pytest.mark.asyncio
async def test_imessage_send_not_linked(monkeypatch):
    monkeypatch.setattr(
        "koraku_cloud.tools.imessage_send_tool.effective_auth_user_sub",
        lambda: "user-1",
    )
    monkeypatch.setattr(
        "koraku_cloud.tools.imessage_send_tool.get_active_channel",
        lambda: None,
    )
    monkeypatch.setattr(
        "koraku_cloud.tools.imessage_send_tool.sendblue_client.configured",
        lambda: True,
    )
    monkeypatch.setattr(
        "koraku_cloud.tools.imessage_send_tool.get_phone_link_for_user_sync",
        lambda _uid: None,
    )
    reset_imessage_send_budget()
    out = await _imessage_send_handler("No OLX reply yet.")
    assert "not linked" in out.lower()


@pytest.mark.asyncio
async def test_imessage_send_limit(monkeypatch):
    monkeypatch.setattr(
        "koraku_cloud.tools.imessage_send_tool.effective_auth_user_sub",
        lambda: "user-1",
    )
    monkeypatch.setattr(
        "koraku_cloud.tools.imessage_send_tool.get_active_channel",
        lambda: None,
    )
    monkeypatch.setattr(
        "koraku_cloud.tools.imessage_send_tool.sendblue_client.configured",
        lambda: True,
    )
    monkeypatch.setattr(
        "koraku_cloud.tools.imessage_send_tool.get_phone_link_for_user_sync",
        lambda _uid: {"phone_e164": "+15551234567", "imessage_thread_id": "t1"},
    )
    async def _send(*_a, **_k):
        return True

    monkeypatch.setattr(
        "koraku_cloud.tools.imessage_send_tool.sendblue_client.send_message",
        _send,
    )
    monkeypatch.setattr(
        "koraku_cloud.tools.imessage_send_tool.append_thread_message_sync",
        lambda **_k: None,
    )
    reset_imessage_send_budget()
    for _ in range(MAX_IMESSAGE_SENDS_PER_RUN):
        assert "Sent" in await _imessage_send_handler("ok")
    out = await _imessage_send_handler("one more")
    assert "limit" in out.lower()
