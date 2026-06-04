import pytest

from koraku_cloud.automations.imessage_notify import (
    IMESSAGE_NOT_LINKED,
    assert_notify_via_imessage_allowed,
    format_automation_imessage_body,
    sanitize_summary_for_imessage_delivery,
)


def test_sanitize_summary_drops_imessage_limitation_paragraph():
    raw = (
        "No OLX emails in the last 30 minutes.\n\n"
        "iMessage limitation: I don't have an active iMessage toolkit.\n\n"
        "What I did: Checked Gmail."
    )
    out = sanitize_summary_for_imessage_delivery(raw)
    assert "No OLX emails" in out
    assert "What I did" in out
    assert "iMessage limitation" not in out


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
