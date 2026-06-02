"""Queue workspace files touched during an iMessage turn for SendBlue attachments."""
from __future__ import annotations

import logging
import os
import re
import shutil
import tempfile
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any

from koraku.channels.context import get_active_channel

log = logging.getLogger(__name__)

MAX_ATTACHMENTS_PER_TURN = 8
MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024

_SKIP_BASENAMES = frozenset(
    {
        ".env",
        ".env.local",
        "credentials.json",
        "id_rsa",
        "id_ed25519",
    }
)

_SKIP_SUFFIXES = (".pem", ".key", ".p12", ".pfx")

_capture: ContextVar["_CaptureState | None"] = ContextVar("koraku_imessage_file_capture", default=None)


@dataclass
class PendingAttachment:
    host_path: str
    display_name: str


@dataclass
class _CaptureState:
    temp_dir: str
    items: list[PendingAttachment]
    seen_realpaths: set[str]


def start_imessage_file_capture() -> Token:
    """Begin tracking Write/Edit outputs for this iMessage turn."""
    state = _CaptureState(
        temp_dir=tempfile.mkdtemp(prefix="koraku-imessage-"),
        items=[],
        seen_realpaths=set(),
    )
    return _capture.set(state)


def end_imessage_file_capture(token: Token) -> None:
    state = _capture.get()
    _capture.reset(token)
    if state is not None and os.path.isdir(state.temp_dir):
        shutil.rmtree(state.temp_dir, ignore_errors=True)


def drain_imessage_attachments() -> list[PendingAttachment]:
    state = _capture.get()
    if state is None:
        return []
    return list(state.items)


def _channel_active() -> bool:
    ch = get_active_channel()
    return ch is not None and ch.kind == "imessage"


def _should_attach_path(host_path: str) -> str | None:
    """Return host_path if attachable, else None."""
    try:
        real = os.path.realpath(host_path)
    except OSError:
        return None
    if not os.path.isfile(real):
        return None
    base = os.path.basename(real)
    if base in _SKIP_BASENAMES or base.startswith("."):
        return None
    lower = base.lower()
    if any(lower.endswith(s) for s in _SKIP_SUFFIXES):
        return None
    try:
        size = os.path.getsize(real)
    except OSError:
        return None
    if size <= 0 or size > MAX_ATTACHMENT_BYTES:
        return None
    return real


def _register_host_file(host_path: str, *, display_name: str | None = None) -> None:
    if not _channel_active():
        return
    state = _capture.get()
    if state is None:
        return
    if len(state.items) >= MAX_ATTACHMENTS_PER_TURN:
        return
    real = _should_attach_path(host_path)
    if not real or real in state.seen_realpaths:
        return
    name = (display_name or os.path.basename(real)).strip() or os.path.basename(real)
    state.seen_realpaths.add(real)
    state.items.append(PendingAttachment(host_path=real, display_name=name))


def record_host_file_if_imessage(host_path: str, *, logical_path: str | None = None) -> None:
    """Record a file written/edited on the API host workspace."""
    name = os.path.basename(logical_path or host_path)
    _register_host_file(host_path, display_name=name)


def record_bytes_if_imessage(data: bytes, display_name: str) -> None:
    """Store bytes in the turn temp dir (e.g. exported from Blaxel)."""
    if not _channel_active() or not data:
        return
    state = _capture.get()
    if state is None or len(state.items) >= MAX_ATTACHMENTS_PER_TURN:
        return
    if len(data) > MAX_ATTACHMENT_BYTES:
        return
    safe = re.sub(r"[^\w.\- ]+", "_", display_name).strip() or "file"
    dest = os.path.join(state.temp_dir, safe)
    base, ext = os.path.splitext(safe)
    n = 0
    while os.path.exists(dest):
        n += 1
        dest = os.path.join(state.temp_dir, f"{base}_{n}{ext}")
    try:
        with open(dest, "wb") as f:
            f.write(data)
    except OSError as e:
        log.warning("imessage attachment temp write failed: %s", e)
        return
    _register_host_file(dest, display_name=safe)


async def export_blaxel_file_if_imessage(sb: Any, sandbox_path: str, logical_path: str) -> None:
    """Read a sandbox file and queue it for iMessage attachment."""
    if not _channel_active():
        return
    name = os.path.basename((logical_path or sandbox_path).replace("\\", "/")) or "file"
    read_bin = getattr(sb.fs, "read_binary", None)
    try:
        if read_bin is not None:
            data = await read_bin(sandbox_path)
            if not isinstance(data, (bytes, bytearray)):
                return
            record_bytes_if_imessage(bytes(data), name)
        else:
            text = await sb.fs.read(sandbox_path)
            record_bytes_if_imessage(text.encode("utf-8"), name)
    except Exception as e:
        log.debug("imessage blaxel export skipped %s: %s", sandbox_path, e)


async def send_queued_imessage_attachments(phone_e164: str) -> int:
    """Upload and send files touched during the current iMessage turn."""
    from koraku.integrations.sendblue_client import send_message, upload_file_path

    pending = drain_imessage_attachments()
    if not pending:
        return 0
    sent = 0
    for att in pending:
        media_url = await upload_file_path(att.host_path)
        if not media_url:
            log.warning("imessage attachment upload failed: %s", att.display_name)
            continue
        caption = f"📎 {att.display_name}"
        if await send_message(phone_e164, caption, media_url=media_url):
            sent += 1
    if sent:
        log.info("imessage sent %s attachment(s)", sent)
    return sent
