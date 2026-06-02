"""Turn SendBlue inbound text + media into agent user input."""
from __future__ import annotations

import logging

from koraku.integrations.voice_transcription import (
    classify_media_url,
    is_voice_media_url,
    transcribe_media_url,
    transcription_configured,
)

log = logging.getLogger(__name__)


async def build_imessage_user_text(*, text: str, media_urls: list[str]) -> str:
    """Merge plain text and transcribed voice notes for the agent."""
    parts: list[str] = []
    if text.strip():
        parts.append(text.strip())

    for url in media_urls:
        url = (url or "").strip()
        if not url:
            continue
        kind = classify_media_url(url)
        if kind == "image":
            parts.append("[User sent an image — image understanding is not available on iMessage yet.]")
            continue
        if is_voice_media_url(url):
            transcript = await transcribe_media_url(url)
            if transcript:
                parts.append(f"[Voice message]: {transcript}")
                log.info("imessage voice transcribed (%s chars)", len(transcript))
            elif transcription_configured():
                parts.append(
                    "[Voice message — I couldn't make out the audio. Try again or type your question.]"
                )
            else:
                parts.append(
                    "[Voice message — transcription is not configured on the server. "
                    "Set FIREWORKS_API_KEY (Whisper) or OPENAI_API_KEY, or type your message.]"
                )
            continue
        parts.append("[User sent an attachment — file handling coming soon.]")

    return "\n\n".join(parts).strip()
