"""SendBlue client helpers."""
from __future__ import annotations

from koraku.integrations.sendblue_client import (
    api_base,
    chunk_text,
    configured,
    normalize_e164,
    resolve_inbound_sender,
    strip_markdown_for_imessage,
    verify_webhook_secret,
)


def test_api_base_default(monkeypatch) -> None:
    from koraku.core.config import settings

    monkeypatch.setattr(settings, "sendblue_api_base", None)
    assert api_base() == "https://api.sendblue.co/api"


def test_api_base_custom(monkeypatch) -> None:
    from koraku.core.config import settings

    monkeypatch.setattr(settings, "sendblue_api_base", "https://custom.sendblue.co")
    assert api_base() == "https://custom.sendblue.co"


def test_api_base_strip_trailing_slash(monkeypatch) -> None:
    from koraku.core.config import settings

    monkeypatch.setattr(settings, "sendblue_api_base", "https://custom.sendblue.co/api/  ")
    assert api_base() == "https://custom.sendblue.co/api"


def test_api_base_fallback_empty(monkeypatch) -> None:
    from koraku.core.config import settings

    monkeypatch.setattr(settings, "sendblue_api_base", "   /  ")
    assert api_base() == "https://api.sendblue.co/api"


def test_resolve_inbound_sender_prefers_number(monkeypatch) -> None:
    from koraku.core.config import settings

    monkeypatch.setattr(settings, "sendblue_from_number", "+13054507715")
    body = {
        "number": "+15551234567",
        "from_number": "+13054507715",
        "is_outbound": False,
    }
    assert resolve_inbound_sender(body) == "+15551234567"


def test_normalize_e164_us() -> None:
    assert normalize_e164("4155551234") == "+14155551234"
    assert normalize_e164("+14155551234") == "+14155551234"


def test_strip_markdown_for_imessage() -> None:
    out = strip_markdown_for_imessage("**Hello** `code`")
    assert "Hello" in out
    assert "`" not in out


def test_chunk_text_splits_long_body() -> None:
    parts = chunk_text("a" * 5000, size=2900)
    assert len(parts) >= 2
    assert sum(len(p) for p in parts) >= 5000


def test_verify_webhook_secret_fail_closed_when_configured(monkeypatch) -> None:
    from koraku.core.config import settings

    monkeypatch.setattr(settings, "sendblue_api_key", "key")
    monkeypatch.setattr(settings, "sendblue_api_secret", "secret")
    monkeypatch.setattr(settings, "sendblue_from_number", "+15551234567")
    monkeypatch.setattr(settings, "sendblue_webhook_secret", "")
    assert configured()
    assert verify_webhook_secret({}) is False


def test_verify_webhook_secret_accepts_matching_header(monkeypatch) -> None:
    from koraku.core.config import settings

    monkeypatch.setattr(settings, "sendblue_api_key", "key")
    monkeypatch.setattr(settings, "sendblue_api_secret", "secret")
    monkeypatch.setattr(settings, "sendblue_from_number", "+15551234567")
    monkeypatch.setattr(settings, "sendblue_webhook_secret", "whsec-test")
    assert verify_webhook_secret({"x-webhook-secret": "whsec-test"}) is True
