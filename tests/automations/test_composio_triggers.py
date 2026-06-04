import pytest

from koraku_cloud.automations.composio_triggers import (
    format_composio_trigger_summary,
    validate_composio_trigger_slug,
)


def test_validate_composio_trigger_slug() -> None:
    assert validate_composio_trigger_slug("gmail_new_gmail_message") == "GMAIL_NEW_GMAIL_MESSAGE"
    with pytest.raises(ValueError, match="Unsupported"):
        validate_composio_trigger_slug("NOT_A_REAL_TRIGGER")


def test_format_gmail_summary() -> None:
    text = format_composio_trigger_summary({
        "trigger_slug": "GMAIL_NEW_GMAIL_MESSAGE",
        "payload": {"subject": "Hello", "from": "a@b.com"},
    })
    assert "GMAIL_NEW_GMAIL_MESSAGE" in text
    assert "Hello" in text
    assert "a@b.com" in text
