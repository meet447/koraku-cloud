"""Voice note transcription helpers."""
from __future__ import annotations

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
    assert "also this" in out
    assert "schedule meeting" in out
