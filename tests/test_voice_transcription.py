"""Voice note transcription helpers."""
from __future__ import annotations

import httpx
import pytest

import koraku.channels.inbound_media as inbound_media
from koraku.integrations import voice_transcription as vt


def test_classify_audio_url() -> None:
    assert vt.classify_media_url("https://cdn.example.com/msg.caf") == "audio"
    assert vt.classify_media_url("https://cdn.example.com/photo.jpg") == "image"


def test_is_voice_media_url() -> None:
    assert vt.is_voice_media_url("https://x.com/a.caf")
    assert not vt.is_voice_media_url("https://x.com/a.jpg")


@pytest.mark.asyncio
async def test_build_imessage_user_text_voice(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_transcribe(url: str) -> str | None:
        return "hello from voice"

    monkeypatch.setattr(inbound_media, "transcription_configured", lambda: True)
    monkeypatch.setattr(inbound_media, "is_voice_media_url", lambda url: True)
    monkeypatch.setattr(inbound_media, "transcribe_media_url", fake_transcribe)

    out = await inbound_media.build_imessage_user_text(
        text="", media_urls=["https://cdn.example.com/v.caf"]
    )
    assert "hello from voice" in out
    assert "[Voice message]" in out


@pytest.mark.asyncio
async def test_build_imessage_user_text_text_and_voice(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake(_url: str) -> str | None:
        return "schedule meeting"

    monkeypatch.setattr(inbound_media, "transcription_configured", lambda: True)
    monkeypatch.setattr(inbound_media, "is_voice_media_url", lambda url: url.endswith(".caf"))
    monkeypatch.setattr(inbound_media, "transcribe_media_url", fake)

    out = await inbound_media.build_imessage_user_text(
        text="also this",
        media_urls=["https://cdn.example.com/v.caf"],
    )
import httpx
from koraku.integrations import voice_transcription as vt

@pytest.mark.asyncio
async def test_download_media_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vt, "validate_inbound_media_url", lambda u: u)

    class MockResponse:
        status_code = 200
        is_success = True
        content = b"fakeaudio"
        headers = {"content-type": "audio/caf"}

    async def mock_get(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    result = await vt.download_media("https://example.com/audio.caf")
    assert result == (b"fakeaudio", "audio/caf")

@pytest.mark.asyncio
async def test_download_media_invalid_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vt, "validate_inbound_media_url", lambda u: None)

    result = await vt.download_media("invalid-url")
    assert result is None

@pytest.mark.asyncio
async def test_download_media_redirect(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vt, "validate_inbound_media_url", lambda u: u)
    monkeypatch.setattr(vt, "validate_redirect_url", lambda u: u)

    class MockRedirectResponse:
        status_code = 301
        is_success = False
        content = b""
        headers = {"location": "https://example.com/redirect.caf"}

    class MockSuccessResponse:
        status_code = 200
        is_success = True
        content = b"fakeaudio"
        headers = {"content-type": "audio/caf"}

    call_count = 0
    async def mock_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return MockRedirectResponse()
        return MockSuccessResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    result = await vt.download_media("https://example.com/audio.caf")
    assert result == (b"fakeaudio", "audio/caf")

@pytest.mark.asyncio
async def test_download_media_redirect_missing_location(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vt, "validate_inbound_media_url", lambda u: u)

    class MockRedirectResponse:
        status_code = 301
        is_success = False
        content = b""
        headers = {}

    async def mock_get(*args, **kwargs):
        return MockRedirectResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    result = await vt.download_media("https://example.com/audio.caf")
    assert result is None

@pytest.mark.asyncio
async def test_download_media_invalid_redirect_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vt, "validate_inbound_media_url", lambda u: u)
    monkeypatch.setattr(vt, "validate_redirect_url", lambda u: None)

    class MockRedirectResponse:
        status_code = 301
        is_success = False
        content = b""
        headers = {"location": "invalid-location"}

    async def mock_get(*args, **kwargs):
        return MockRedirectResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    result = await vt.download_media("https://example.com/audio.caf")
    assert result is None

@pytest.mark.asyncio
async def test_download_media_too_many_redirects(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vt, "validate_inbound_media_url", lambda u: u)
    monkeypatch.setattr(vt, "validate_redirect_url", lambda u: u)

    class MockRedirectResponse:
        status_code = 301
        is_success = False
        content = b""
        headers = {"location": "https://example.com/loop.caf"}

    async def mock_get(*args, **kwargs):
        return MockRedirectResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    result = await vt.download_media("https://example.com/audio.caf")
    assert result is None

@pytest.mark.asyncio
async def test_download_media_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vt, "validate_inbound_media_url", lambda u: u)

    async def mock_get(*args, **kwargs):
        raise httpx.HTTPError("network error")

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    result = await vt.download_media("https://example.com/audio.caf")
    assert result is None

@pytest.mark.asyncio
async def test_download_media_not_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vt, "validate_inbound_media_url", lambda u: u)

    class MockErrorResponse:
        status_code = 404
        is_success = False
        content = b""
        headers = {}

    async def mock_get(*args, **kwargs):
        return MockErrorResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    result = await vt.download_media("https://example.com/audio.caf")
    assert result is None

@pytest.mark.asyncio
async def test_download_media_too_large(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vt, "validate_inbound_media_url", lambda u: u)

    class MockLargeResponse:
        status_code = 200
        is_success = True
        content = b"a" * (vt.MAX_AUDIO_BYTES + 1)
        headers = {"content-type": "audio/caf"}

    async def mock_get(*args, **kwargs):
        return MockLargeResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    result = await vt.download_media("https://example.com/audio.caf")
    assert result is None
