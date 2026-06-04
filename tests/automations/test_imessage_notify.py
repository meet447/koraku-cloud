import pytest

from koraku_cloud.automations.imessage_notify import (
    IMESSAGE_NOT_LINKED,
    assert_notify_via_imessage_allowed,
    format_automation_imessage_body,
)


def test_format_automation_imessage_body_success():
    text = format_automation_imessage_body(
        title="Daily brief",
        status="success",
        result_summary="Three meetings today.",
        error=None,
    )
    assert "[Koraku] Daily brief" in text
    assert "Three meetings today." in text


def test_format_automation_imessage_body_failed():
    text = format_automation_imessage_body(
        title="Inbox",
        status="failed",
        result_summary=None,
        error="LLM timeout",
    )
    assert "failed" in text.lower()
    assert "LLM timeout" in text


def test_assert_notify_via_imessage_not_linked(monkeypatch):
    monkeypatch.setattr(
        "koraku_cloud.automations.imessage_notify.sendblue_client.configured",
        lambda: True,
    )
    monkeypatch.setattr(
        "koraku_cloud.automations.imessage_notify.user_imessage_phone_sync",
        lambda _uid: None,
    )
    with pytest.raises(ValueError, match=IMESSAGE_NOT_LINKED):
        assert_notify_via_imessage_allowed("user-1")


def test_assert_notify_via_imessage_not_configured(monkeypatch):
    monkeypatch.setattr(
        "koraku_cloud.automations.imessage_notify.sendblue_client.configured",
        lambda: False,
    )
    with pytest.raises(ValueError, match="SendBlue is not configured"):
        assert_notify_via_imessage_allowed("user-1")
