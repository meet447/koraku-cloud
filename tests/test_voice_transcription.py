"""Voice note transcription helpers."""
from __future__ import annotations

import pytest

import httpx
import respx

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
    assert "also this" in out
    assert "schedule meeting" in out

@pytest.mark.asyncio
async def test_transcribe_audio_bytes_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vt, "_credentials", lambda: ("https://api.example.com/v1", "testkey", "testmodel"))

    with respx.mock:
        route = respx.post("https://api.example.com/v1/audio/transcriptions").mock(
            return_value=httpx.Response(200, json={"text": "hello transcribed text"})
        )

        result = await vt.transcribe_audio_bytes(b"fakeaudio", filename="test.caf")

        assert result == "hello transcribed text"
        assert route.called

@pytest.mark.asyncio
async def test_transcribe_audio_bytes_no_creds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vt, "_credentials", lambda: None)

    result = await vt.transcribe_audio_bytes(b"fakeaudio")
    assert result is None

@pytest.mark.asyncio
async def test_transcribe_audio_bytes_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vt, "_credentials", lambda: ("https://api.example.com/v1", "testkey", "testmodel"))

    with respx.mock:
        route = respx.post("https://api.example.com/v1/audio/transcriptions").mock(
            side_effect=httpx.HTTPError("Connection failed")
        )

        result = await vt.transcribe_audio_bytes(b"fakeaudio")

        assert result is None
        assert route.called

@pytest.mark.asyncio
async def test_transcribe_audio_bytes_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vt, "_credentials", lambda: ("https://api.example.com/v1", "testkey", "testmodel"))

    with respx.mock:
        route = respx.post("https://api.example.com/v1/audio/transcriptions").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        result = await vt.transcribe_audio_bytes(b"fakeaudio")

        assert result is None
        assert route.called

@pytest.mark.asyncio
async def test_transcribe_audio_bytes_bad_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vt, "_credentials", lambda: ("https://api.example.com/v1", "testkey", "testmodel"))

    with respx.mock:
        route1 = respx.post("https://api.example.com/v1/audio/transcriptions").mock(
            return_value=httpx.Response(200, text="not valid json")
        )

        result1 = await vt.transcribe_audio_bytes(b"fakeaudio")
        assert result1 is None
        assert route1.called

        route2 = respx.post("https://api.example.com/v1/audio/transcriptions").mock(
            return_value=httpx.Response(200, json={"wrong_key": "some text"})
        )

        result2 = await vt.transcribe_audio_bytes(b"fakeaudio")
        assert result2 is None
        assert route2.called
