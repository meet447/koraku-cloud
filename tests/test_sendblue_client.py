"""SendBlue client helpers."""
from __future__ import annotations

from unittest.mock import mock_open

import httpx
import pytest

from koraku.integrations.sendblue_client import (
    chunk_text,
    configured,
    normalize_e164,
    resolve_inbound_sender,
    strip_markdown_for_imessage,
    upload_file_path,
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


@pytest.mark.asyncio
async def test_upload_file_path_missing_credentials(mocker) -> None:
    mocker.patch("koraku.integrations.sendblue_client._headers", return_value=None)
    assert await upload_file_path("dummy.txt") is None

@pytest.mark.asyncio
async def test_upload_file_path_missing_file(mocker) -> None:
    mocker.patch("koraku.integrations.sendblue_client._headers", return_value={"Content-Type": "application/json", "sb-api-key-id": "key", "sb-api-secret-key": "secret"})
    mocker.patch("os.path.isfile", return_value=False)
    assert await upload_file_path("dummy.txt") is None

@pytest.mark.asyncio
async def test_upload_file_path_httpx_error(mocker) -> None:
    mocker.patch("koraku.integrations.sendblue_client._headers", return_value={"Content-Type": "application/json", "sb-api-key-id": "key", "sb-api-secret-key": "secret"})
    mocker.patch("os.path.isfile", return_value=True)
    mocker.patch("builtins.open", mock_open(read_data=b"data"))
    mocker.patch("httpx.AsyncClient.post", side_effect=httpx.HTTPError("Mocked error"))
    assert await upload_file_path("dummy.txt") is None

@pytest.mark.asyncio
async def test_upload_file_path_http_failure(mocker) -> None:
    mocker.patch("koraku.integrations.sendblue_client._headers", return_value={"Content-Type": "application/json", "sb-api-key-id": "key", "sb-api-secret-key": "secret"})
    mocker.patch("os.path.isfile", return_value=True)
    mocker.patch("builtins.open", mock_open(read_data=b"data"))
    mock_res = mocker.Mock()
    mock_res.is_success = False
    mock_res.status_code = 400
    mock_res.text = "Error"
    mocker.patch("httpx.AsyncClient.post", return_value=mock_res)
    assert await upload_file_path("dummy.txt") is None

@pytest.mark.asyncio
async def test_upload_file_path_invalid_json(mocker) -> None:
    mocker.patch("koraku.integrations.sendblue_client._headers", return_value={"Content-Type": "application/json", "sb-api-key-id": "key", "sb-api-secret-key": "secret"})
    mocker.patch("os.path.isfile", return_value=True)
    mocker.patch("builtins.open", mock_open(read_data=b"data"))
    mock_res = mocker.Mock()
    mock_res.is_success = True
    mock_res.json.side_effect = Exception("Mocked exception")
    mocker.patch("httpx.AsyncClient.post", return_value=mock_res)
    assert await upload_file_path("dummy.txt") is None

@pytest.mark.asyncio
async def test_upload_file_path_success(mocker) -> None:
    mocker.patch("koraku.integrations.sendblue_client._headers", return_value={"Content-Type": "application/json", "sb-api-key-id": "key", "sb-api-secret-key": "secret"})
    mocker.patch("os.path.isfile", return_value=True)
    mocker.patch("builtins.open", mock_open(read_data=b"data"))
    mock_res = mocker.Mock()
    mock_res.is_success = True
    mock_res.json.return_value = {"media_url": "https://example.com/file.png"}
    mocker.patch("httpx.AsyncClient.post", return_value=mock_res)
    assert await upload_file_path("dummy.txt") == "https://example.com/file.png"
