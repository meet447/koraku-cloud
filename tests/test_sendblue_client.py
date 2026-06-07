"""SendBlue client helpers."""
from __future__ import annotations

from koraku.integrations.sendblue_client import (
    chunk_text,
    configured,
    normalize_e164,
    resolve_inbound_sender,
    strip_markdown_for_imessage,
    verify_webhook_secret,
)


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

import pytest
import httpx
from koraku.integrations.sendblue_client import send_typing_indicator

@pytest.mark.asyncio
async def test_send_typing_indicator_missing_config(monkeypatch) -> None:
    from koraku.core.config import settings

    monkeypatch.setattr(settings, "sendblue_api_key", "")
    monkeypatch.setattr(settings, "sendblue_api_secret", "")
    monkeypatch.setattr(settings, "sendblue_from_number", "")

    # Should return early without raising exceptions
    await send_typing_indicator("+15551234567")

@pytest.mark.asyncio
async def test_send_typing_indicator_success(monkeypatch, mocker) -> None:
    from koraku.core.config import settings

    monkeypatch.setattr(settings, "sendblue_api_key", "key")
    monkeypatch.setattr(settings, "sendblue_api_secret", "secret")
    monkeypatch.setattr(settings, "sendblue_from_number", "+15551234567")

    mock_post = mocker.patch("httpx.AsyncClient.post")
    mock_response = mocker.Mock()
    mock_response.is_success = True
    mock_post.return_value = mock_response

    await send_typing_indicator("+15559999999")

    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == "https://api.sendblue.co/api/send-typing-indicator"
    assert kwargs["headers"] == {
        "Content-Type": "application/json",
        "sb-api-key-id": "key",
        "sb-api-secret-key": "secret",
    }
    assert kwargs["json"] == {
        "number": "+15559999999",
        "from_number": "+15551234567",
    }

@pytest.mark.asyncio
async def test_send_typing_indicator_api_error(monkeypatch, mocker) -> None:
    from koraku.core.config import settings

    monkeypatch.setattr(settings, "sendblue_api_key", "key")
    monkeypatch.setattr(settings, "sendblue_api_secret", "secret")
    monkeypatch.setattr(settings, "sendblue_from_number", "+15551234567")

    mock_post = mocker.patch("httpx.AsyncClient.post")
    mock_response = mocker.Mock()
    mock_response.is_success = False
    mock_response.status_code = 400
    mock_response.text = "Bad Request"
    mock_post.return_value = mock_response

    mock_log = mocker.patch("koraku.integrations.sendblue_client.log")

    await send_typing_indicator("+15559999999")

    mock_post.assert_called_once()
    mock_log.debug.assert_called_once_with("sendblue typing %s: %s", 400, "Bad Request")

@pytest.mark.asyncio
async def test_send_typing_indicator_http_error(monkeypatch, mocker) -> None:
    from koraku.core.config import settings

    monkeypatch.setattr(settings, "sendblue_api_key", "key")
    monkeypatch.setattr(settings, "sendblue_api_secret", "secret")
    monkeypatch.setattr(settings, "sendblue_from_number", "+15551234567")

    mock_post = mocker.patch("httpx.AsyncClient.post")
    error = httpx.HTTPError("Network Error")
    mock_post.side_effect = error

    mock_log = mocker.patch("koraku.integrations.sendblue_client.log")

    await send_typing_indicator("+15559999999")

    mock_post.assert_called_once()
    mock_log.debug.assert_called_once_with("sendblue typing failed: %s", error)
