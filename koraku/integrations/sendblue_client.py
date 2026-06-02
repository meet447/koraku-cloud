"""SendBlue REST client for iMessage / SMS outbound and typing indicators."""
from __future__ import annotations

import logging
import os
import re
from typing import Any

import httpx

from koraku.core.config import settings

log = logging.getLogger(__name__)

MAX_CHUNK = 2900


def api_base() -> str:
    raw = (settings.sendblue_api_base or "https://api.sendblue.co/api").strip().rstrip("/")
    return raw or "https://api.sendblue.co/api"


def configured() -> bool:
    return bool(
        (settings.sendblue_api_key or "").strip()
        and (settings.sendblue_api_secret or "").strip()
        and (settings.sendblue_from_number or "").strip()
    )


def resolve_inbound_sender(body: dict[str, Any]) -> str | None:
    """End-user phone for an inbound webhook (SendBlue ``number`` field)."""
    koraku = normalize_e164(settings.sendblue_from_number)
    for key in ("number", "from_number"):
        raw = body.get(key)
        if raw is None or raw == "":
            continue
        phone = normalize_e164(str(raw))
        if phone and phone != koraku:
            return phone
    return None


def normalize_e164(raw: str | None) -> str | None:
    if not raw:
        return None
    trimmed = raw.strip()
    if not trimmed:
        return None
    if trimmed.startswith("+"):
        return trimmed
    digits = re.sub(r"\D", "", trimmed)
    if len(digits) == 10:
        return f"+1{digits}"
    if 11 <= len(digits) <= 15:
        return f"+{digits}"
    return trimmed


def _headers() -> dict[str, str] | None:
    key = (settings.sendblue_api_key or "").strip()
    secret = (settings.sendblue_api_secret or "").strip()
    if not key or not secret:
        return None
    return {
        "Content-Type": "application/json",
        "sb-api-key-id": key,
        "sb-api-secret-key": secret,
    }


def strip_markdown_for_imessage(text: str) -> str:
    s = text or ""
    s = re.sub(r"```[\s\S]*?```", lambda m: re.sub(r"```\w*\n?|```", "", m.group(0)), s)
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"\*(.+?)\*", r"\1", s)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    s = re.sub(r"^#+\s+", "", s, flags=re.MULTILINE)
    s = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1 (\2)", s)
    return s.strip()


def chunk_text(text: str, size: int = MAX_CHUNK) -> list[str]:
    if len(text) <= size:
        return [text] if text else []
    out: list[str] = []
    buf = ""
    for line in text.split("\n"):
        while len(line) > size:
            if buf:
                out.append(buf)
                buf = ""
            out.append(line[:size])
            line = line[size:]
        candidate = f"{buf}\n{line}" if buf else line
        if len(candidate) > size:
            if buf:
                out.append(buf)
            buf = line
        else:
            buf = candidate
    if buf:
        out.append(buf)
    return out


async def upload_file_path(local_path: str) -> str | None:
    """Upload a local file to SendBlue CDN; returns ``media_url`` on success."""
    h = _headers()
    if not h:
        return None
    path = os.path.abspath(local_path)
    if not os.path.isfile(path):
        return None
    auth = {k: v for k, v in h.items() if k.lower() != "content-type"}
    try:
        with open(path, "rb") as fh:
            async with httpx.AsyncClient(timeout=120.0) as client:
                res = await client.post(
                    f"{api_base()}/upload-file",
                    headers=auth,
                    files={"file": (os.path.basename(path), fh)},
                )
    except httpx.HTTPError as e:
        log.warning("sendblue upload failed: %s", e)
        return None
    if not res.is_success:
        log.warning("sendblue upload %s: %s", res.status_code, res.text[:400])
        return None
    try:
        body = res.json()
    except Exception:
        return None
    if isinstance(body, dict):
        url = body.get("media_url")
        if isinstance(url, str) and url.strip():
            return url.strip()
    return None


async def send_message(
    to_number: str,
    text: str,
    *,
    media_url: str | None = None,
) -> bool:
    h = _headers()
    from_num = normalize_e164(settings.sendblue_from_number)
    to = normalize_e164(to_number)
    if not h or not from_num or not to:
        log.warning("sendblue send skipped: missing credentials or numbers")
        return False
    media = (media_url or "").strip() or None
    plain = strip_markdown_for_imessage(text) if text else ""
    if not plain and not media:
        return False
    if media and not plain:
        plain = " "
    parts = chunk_text(plain) if plain.strip() else [" "]
    ok = True
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, part in enumerate(parts):
            payload: dict[str, str] = {
                "number": to,
                "content": part,
                "from_number": from_num,
            }
            if media and i == 0:
                payload["media_url"] = media
            try:
                res = await client.post(
                    f"{api_base()}/send-message",
                    headers=h,
                    json=payload,
                )
            except httpx.HTTPError as e:
                log.warning("sendblue send failed: %s", e)
                ok = False
                continue
            if not res.is_success:
                detail = res.text[:400]
                log.warning("sendblue send %s: %s", res.status_code, detail)
                if res.status_code == 400 and "verified" in detail.lower():
                    log.warning(
                        "sendblue: add %s as a verified contact (free plan). "
                        "Dashboard → Contacts, or: sendblue add-contact %s",
                        to,
                        to,
                    )
                ok = False
    return ok


async def send_typing_indicator(to_number: str) -> None:
    h = _headers()
    from_num = normalize_e164(settings.sendblue_from_number)
    to = normalize_e164(to_number)
    if not h or not from_num or not to:
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{api_base()}/send-typing-indicator",
                headers=h,
                json={"number": to, "from_number": from_num},
            )
    except httpx.HTTPError:
        pass


class TypingLoop:
    def __init__(self, to_number: str) -> None:
        self._to = to_number
        self._timer: Any = None

    async def start(self) -> None:
        await send_typing_indicator(self._to)

    def arm(self, loop) -> None:
        import asyncio

        async def _tick() -> None:
            await send_typing_indicator(self._to)

        self._timer = loop.call_later(5.0, lambda: loop.create_task(_tick()))

    def stop(self, loop) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None


def verify_webhook_secret(headers: dict[str, str]) -> bool:
    secret = (settings.sendblue_webhook_secret or "").strip()
    if not secret:
        return True
    for name in ("x-webhook-secret", "sb-signing-secret", "x-sendblue-signature"):
        val = headers.get(name) or headers.get(name.lower())
        if val and val.strip() == secret:
            return True
    return False
