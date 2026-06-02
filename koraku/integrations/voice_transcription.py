"""Transcribe inbound iMessage voice notes (Whisper-compatible APIs)."""
from __future__ import annotations

import logging
import os
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from koraku.core.config import settings
from koraku.integrations.inbound_media_url import validate_inbound_media_url, validate_redirect_url

log = logging.getLogger(__name__)

MAX_AUDIO_BYTES = 15 * 1024 * 1024

AUDIO_EXTENSIONS = frozenset(
    {".caf", ".m4a", ".mp4", ".aac", ".mp3", ".wav", ".ogg", ".opus", ".amr", ".mpeg", ".mpga"}
)
IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".gif", ".heic", ".webp", ".bmp"})


def transcription_configured() -> bool:
    return _credentials() is not None


def _credentials() -> tuple[str, str, str] | None:
    """Return (api_base, api_key, model) for OpenAI-style ``/audio/transcriptions``."""
    if not settings.imessage_voice_transcription_enabled:
        return None
    fw = (settings.fireworks_api_key or "").strip()
    if fw:
        base = (settings.voice_transcription_base_url or "https://audio-prod.api.fireworks.ai/v1").rstrip(
            "/"
        )
        model = (settings.voice_transcription_model or "whisper-large-v3").strip()
        return base, fw, model
    oai = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if oai:
        base = (os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        return base, oai, "whisper-1"
    return None


def _ext_from_url(url: str) -> str:
    path = urlparse(url).path or ""
    return PurePosixPath(path).suffix.lower()


def classify_media_url(url: str) -> str:
    """``audio`` | ``image`` | ``other``."""
    ext = _ext_from_url(url)
    if ext in AUDIO_EXTENSIONS:
        return "audio"
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in (".pdf", ".doc", ".docx", ".txt", ".vcf"):
        return "other"
    return "other"


def _filename_for_url(url: str, content_type: str | None) -> str:
    ext = _ext_from_url(url)
    if not ext and content_type:
        ct = content_type.split(";")[0].strip().lower()
        if "caf" in ct or ct == "audio/x-caf":
            ext = ".caf"
        elif "mpeg" in ct or ct == "audio/mp3":
            ext = ".mp3"
        elif "mp4" in ct or ct == "audio/mp4":
            ext = ".m4a"
        elif ct.startswith("audio/"):
            ext = ".m4a"
    return f"voice{ext or '.caf'}"


_REDIRECT_STATUS = frozenset({301, 302, 303, 307, 308})
_MAX_REDIRECTS = 5


async def download_media(url: str) -> tuple[bytes, str | None] | None:
    current = validate_inbound_media_url(url)
    if not current:
        return None
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=False) as client:
            res: httpx.Response | None = None
            for _ in range(_MAX_REDIRECTS + 1):
                res = await client.get(current)
                if res.status_code in _REDIRECT_STATUS:
                    location = (res.headers.get("location") or "").strip()
                    if not location:
                        log.warning("inbound media redirect missing Location header")
                        return None
                    nxt = validate_redirect_url(urljoin(current, location))
                    if not nxt:
                        return None
                    current = nxt
                    continue
                break
    except httpx.HTTPError as e:
        log.warning("voice media download failed: %s", e)
        return None
    if res is None or not res.is_success:
        code = res.status_code if res is not None else "?"
        log.warning("voice media download %s: %s", code, url[:120])
        return None
    data = res.content
    if len(data) > MAX_AUDIO_BYTES:
        log.warning("voice media too large (%s bytes)", len(data))
        return None
    return data, res.headers.get("content-type")


async def transcribe_audio_bytes(data: bytes, *, filename: str = "voice.caf") -> str | None:
    creds = _credentials()
    if not creds:
        return None
    base, key, model = creds
    url = f"{base}/audio/transcriptions"
    headers = {"Authorization": f"Bearer {key}"}
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            res = await client.post(
                url,
                headers=headers,
                files={"file": (filename, data)},
                data={"model": model},
            )
    except httpx.HTTPError as e:
        log.warning("voice transcription request failed: %s", e)
        return None
    if not res.is_success:
        log.warning("voice transcription %s: %s", res.status_code, res.text[:300])
        return None
    try:
        body = res.json()
    except Exception:
        return None
    if isinstance(body, dict):
        text = body.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
    return None


def is_voice_media_url(url: str) -> bool:
    if classify_media_url(url) == "image":
        return False
    if classify_media_url(url) == "audio":
        return True
    lower = url.lower()
    return any(ext in lower for ext in AUDIO_EXTENSIONS) or "audio" in lower or "voice" in lower


async def transcribe_media_url(url: str) -> str | None:
    if not is_voice_media_url(url):
        return None
    downloaded = await download_media(url)
    if not downloaded:
        return None
    data, content_type = downloaded
    ct = (content_type or "").lower()
    if ct.startswith("image/"):
        return None
    name = _filename_for_url(url, content_type)
    return await transcribe_audio_bytes(data, filename=name)
