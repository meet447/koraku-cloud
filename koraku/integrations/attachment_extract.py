"""Extract text from user-uploaded files (chat JSON or iMessage URLs)."""
from __future__ import annotations

import base64
import io
import logging
import re
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

from koraku.core.config import settings

log = logging.getLogger(__name__)

_ALLOWED_CHAT_MIMES = frozenset(
    {
        "application/pdf",
        "text/plain",
        "text/markdown",
        "text/csv",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
)

_EXT_TO_MIME = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".csv": "text/csv",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

_DOCUMENT_EXTENSIONS = frozenset(_EXT_TO_MIME.keys())


@dataclass(frozen=True)
class ExtractedAttachment:
    filename: str
    media_type: str
    text: str
    truncated: bool = False
    error: str | None = None
    workspace_path: str | None = None


def _max_bytes_chat() -> int:
    return max(64_000, int(getattr(settings, "chat_attachment_max_bytes", 8 * 1024 * 1024)))


def _max_bytes_imessage() -> int:
    return max(64_000, int(getattr(settings, "imessage_attachment_max_bytes", 15 * 1024 * 1024)))


def _excerpt_chars() -> int:
    return max(2_000, int(getattr(settings, "chat_attachment_excerpt_chars", 24_000)))


def sanitize_filename(name: str) -> str:
    raw = (name or "attachment").strip().replace("\\", "/").split("/")[-1]
    raw = re.sub(r"[^\w.\- ()]", "_", raw)
    return (raw[:180] or "attachment").strip() or "attachment"


def resolve_media_type(filename: str, media_type: str | None) -> str:
    mt = (media_type or "").strip().lower().split(";")[0]
    if mt in _ALLOWED_CHAT_MIMES:
        return mt
    ext = PurePosixPath(sanitize_filename(filename)).suffix.lower()
    return _EXT_TO_MIME.get(ext, mt or "application/octet-stream")


def is_supported_attachment(filename: str, media_type: str | None = None) -> bool:
    mt = resolve_media_type(filename, media_type)
    if mt in _ALLOWED_CHAT_MIMES:
        return True
    ext = PurePosixPath(sanitize_filename(filename)).suffix.lower()
    return ext in _DOCUMENT_EXTENSIONS


def classify_attachment_url(url: str) -> str:
    """``document`` | ``audio`` | ``image`` | ``other``."""
    from koraku.integrations.voice_transcription import classify_media_url

    kind = classify_media_url(url)
    if kind in ("audio", "image"):
        return kind
    ext = PurePosixPath(urlparse(url).path or "").suffix.lower()
    if ext in _DOCUMENT_EXTENSIONS:
        return "document"
    return "other"


def _truncate_excerpt(text: str) -> tuple[str, bool]:
    cap = _excerpt_chars()
    clean = (text or "").strip()
    if len(clean) <= cap:
        return clean, False
    return clean[: cap - 40].rstrip() + "\n\n[… attachment excerpt truncated …]", True


def _extract_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n\n".join(parts).strip()


def _extract_docx(data: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(data))
    parts: list[str] = []
    for para in doc.paragraphs:
        t = (para.text or "").strip()
        if t:
            parts.append(t)
    return "\n\n".join(parts).strip()


def extract_text_from_bytes(
    data: bytes,
    *,
    filename: str,
    media_type: str | None = None,
) -> ExtractedAttachment:
    name = sanitize_filename(filename)
    mt = resolve_media_type(name, media_type)
    if not is_supported_attachment(name, mt):
        return ExtractedAttachment(
            filename=name,
            media_type=mt,
            text="",
            error=f"Unsupported attachment type ({mt or 'unknown'}). Use PDF, DOCX, TXT, MD, or CSV.",
        )
    if len(data) > _max_bytes_chat():
        return ExtractedAttachment(
            filename=name,
            media_type=mt,
            text="",
            error=f"Attachment exceeds { _max_bytes_chat() // (1024 * 1024)}MB limit.",
        )
    try:
        if mt == "application/pdf" or name.lower().endswith(".pdf"):
            body = _extract_pdf(data)
        elif mt.endswith("wordprocessingml.document") or name.lower().endswith(".docx"):
            body = _extract_docx(data)
        else:
            body = data.decode("utf-8", errors="replace").strip()
    except ImportError as e:
        log.warning("attachment extract missing dependency: %s", e)
        return ExtractedAttachment(
            filename=name,
            media_type=mt,
            text="",
            error="Server missing document libraries (install koraku[artifacts]).",
        )
    except Exception as e:
        log.warning("attachment extract failed for %s: %s", name, e)
        return ExtractedAttachment(
            filename=name,
            media_type=mt,
            text="",
            error=f"Could not read attachment: {e}",
        )
    if not body.strip():
        return ExtractedAttachment(
            filename=name,
            media_type=mt,
            text="",
            error="No extractable text found in this file.",
        )
    excerpt, truncated = _truncate_excerpt(body)
    return ExtractedAttachment(
        filename=name,
        media_type=mt,
        text=excerpt,
        truncated=truncated,
    )


def save_attachment_to_workspace(data: bytes, filename: str, workspace: str) -> str | None:
    if not bool(getattr(settings, "chat_attachment_save_to_workspace", True)):
        return None
    ws = Path(workspace).resolve()
    if not ws.is_dir():
        return None
    safe = sanitize_filename(filename)
    rel_dir = Path("uploads") / "inbound"
    dest_dir = ws / rel_dir
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{uuid.uuid4().hex[:10]}_{safe}"
        dest.write_bytes(data)
        return str(rel_dir / dest.name).replace("\\", "/")
    except OSError as e:
        log.warning("could not save attachment to workspace: %s", e)
        return None


def extract_chat_attachment_part(
    *,
    filename: str,
    media_type: str,
    data_b64: str,
    workspace: str | None = None,
) -> ExtractedAttachment:
    name = sanitize_filename(filename)
    if not is_supported_attachment(name, media_type):
        return ExtractedAttachment(
            filename=name,
            media_type=media_type,
            text="",
            error="Unsupported file type.",
        )
    try:
        raw = base64.b64decode(data_b64, validate=True)
    except Exception:
        return ExtractedAttachment(
            filename=name,
            media_type=media_type,
            text="",
            error="Invalid base64 attachment payload.",
        )
    row = extract_text_from_bytes(raw, filename=name, media_type=media_type)
    if workspace and not row.error:
        path = save_attachment_to_workspace(raw, name, workspace)
        if path:
            return ExtractedAttachment(
                filename=row.filename,
                media_type=row.media_type,
                text=row.text,
                truncated=row.truncated,
                error=row.error,
                workspace_path=path,
            )
    return row


def process_chat_attachments(
    parts: list[dict[str, Any]],
    *,
    workspace: str | None = None,
) -> str:
    """Build markdown context from chat ``attachments`` JSON objects."""
    if not parts:
        return ""
    blocks: list[str] = []
    for item in parts[: max(1, int(getattr(settings, "chat_attachment_max_per_message", 4)))]:
        if not isinstance(item, dict):
            continue
        row = extract_chat_attachment_part(
            filename=str(item.get("filename") or "attachment"),
            media_type=str(item.get("media_type") or ""),
            data_b64=str(item.get("data") or ""),
            workspace=workspace,
        )
        blocks.append(_format_one_attachment(row))
    if not blocks:
        return ""
    return "## Attachments\n" + "\n\n".join(blocks)


def _format_one_attachment(row: ExtractedAttachment) -> str:
    header = f"### {row.filename}"
    if row.workspace_path:
        header += f"\nSaved in workspace: `{row.workspace_path}`"
    if row.error:
        return f"{header}\nError: {row.error}"
    note = " (excerpt)" if row.truncated else ""
    return f"{header}{note}\n```\n{row.text}\n```"


async def extract_attachment_from_url(url: str) -> str | None:
    """Download and extract a document attachment URL (iMessage / SendBlue)."""
    from koraku.integrations.voice_transcription import download_media_bytes

    downloaded = await download_media_bytes(url, max_bytes=_max_bytes_imessage())
    if not downloaded:
        return None
    data, content_type = downloaded
    path = urlparse(url).path or ""
    filename = sanitize_filename(PurePosixPath(path).name or "attachment")
    if not is_supported_attachment(filename, content_type):
        return None
    row = extract_text_from_bytes(data, filename=filename, media_type=content_type)
    if row.error:
        return f"[Attachment {row.filename}: {row.error}]"
    formatted = _format_one_attachment(row)
    return formatted.replace("### ", "[Attachment: ", 1).replace("\n", "\n", 1)
