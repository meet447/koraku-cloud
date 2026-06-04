"""Cloud workspace file tree + read (Blaxel session folder)."""
from __future__ import annotations

import asyncio
import posixpath
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import Response

from koraku.core.config import settings
from koraku_cloud.api.auth_scope import cloud_supabase_user_scope
from koraku.integrations.blaxel_runtime import (
    cloud_blaxel_block_reason,
    ensure_session_workspace,
    workspace_root_posix_for_channel,
)
from koraku_cloud.integrations.supabase_external import resolve_thread_channel_sync
from koraku.integrations.cloud_user import (
    effective_auth_user_sub,
    effective_cloud_user_id,
    workspace_path_user_id,
)

router = APIRouter(prefix="/api/workspace", tags=["workspace"])

_MAX_TEXT_FILE_BYTES = 2 * 1024 * 1024
_MAX_BLOB_FILE_BYTES = 12 * 1024 * 1024

_BLOB_MEDIA = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    # Raster / vector images (workspace preview + download)
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".jpe": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".avif": "image/avif",
    ".bmp": "image/bmp",
    ".ico": "image/x-icon",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".svg": "image/svg+xml",
    ".heic": "image/heic",
    ".heif": "image/heif",
    ".jfif": "image/jpeg",
    ".apng": "image/apng",
}


def _parse_session_id(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        raise HTTPException(status_code=400, detail="session_id is required")
    try:
        uuid.UUID(s)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="session_id must be a UUID") from e
    return s


async def _workspace_context(session_id: str) -> tuple[str, str, str]:
    """Resolve Blaxel root path, channel, and path user id for a chat thread."""
    storage_uid = effective_cloud_user_id()
    auth_uid = effective_auth_user_sub()
    channel = await asyncio.to_thread(resolve_thread_channel_sync, session_id, auth_uid)
    path_uid = workspace_path_user_id(storage_uid, channel)
    root = workspace_root_posix_for_channel(path_uid, session_id, channel, settings)
    return root, channel, path_uid


async def _ensure_workspace_sandbox(session_id: str, user_id: str, channel: str) -> Any:
    sb, _root = await ensure_session_workspace(
        session_id,
        settings,
        user_id=user_id,
        channel=channel,
    )
    return sb


from koraku.workspace.safe_paths import safe_join_under_session_root


def _require_cloud_workspace() -> None:
    reason = cloud_blaxel_block_reason(settings)
    if reason:
        raise HTTPException(status_code=503, detail=reason)


async def _workspace_user_scope(
    request: Request,
    authorization: str | None = Header(None),
) -> AsyncGenerator[None, None]:
    """Require Blaxel + valid Supabase JWT; match chat sandbox path (org + user)."""
    async for _scope in cloud_supabase_user_scope(
        request,
        authorization,
        pre_check=_require_cloud_workspace,
    ):
        yield


@router.get("/tree", dependencies=[Depends(_workspace_user_scope)])
async def workspace_tree(
    session_id: str = Query(..., min_length=8),
    path: str = Query("", max_length=2048),
) -> dict[str, Any]:
    """List files and subdirectories under the chat session folder (or a subpath)."""
    sid = _parse_session_id(session_id)
    root, channel, path_uid = await _workspace_context(sid)
    target = safe_join_under_session_root(root, path)
    try:
        sb = await _ensure_workspace_sandbox(sid, path_uid, channel)
        directory = await sb.fs.ls(target)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Blaxel: {e}") from e

    files = [
        {"name": f.name, "path": f.path, "size": getattr(f, "size", 0)}
        for f in (directory.files or [])
    ]
    dirs = [{"name": d.name, "path": d.path} for d in (directory.subdirectories or [])]
    return {"root": root, "path": target, "files": files, "directories": dirs}


@router.get("/file", dependencies=[Depends(_workspace_user_scope)])
async def workspace_read_file(
    session_id: str = Query(..., min_length=8),
    path: str = Query(..., min_length=1, max_length=2048),
) -> dict[str, Any]:
    """Read a text file under the session workspace (size-capped)."""
    sid = _parse_session_id(session_id)
    root, channel, path_uid = await _workspace_context(sid)
    target = safe_join_under_session_root(root, path)
    try:
        sb = await _ensure_workspace_sandbox(sid, path_uid, channel)
        text = await sb.fs.read(target)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Blaxel: {e}") from e

    raw = text if isinstance(text, str) else str(text)
    truncated = len(raw.encode("utf-8")) > _MAX_TEXT_FILE_BYTES
    if truncated:
        raw = raw.encode("utf-8")[:_MAX_TEXT_FILE_BYTES].decode("utf-8", errors="replace")
    return {"path": target, "content": raw, "truncated": truncated}


@router.get("/file/blob", dependencies=[Depends(_workspace_user_scope)])
async def workspace_read_blob(
    session_id: str = Query(..., min_length=8),
    path: str = Query(..., min_length=1, max_length=2048),
) -> Response:
    """Return raw bytes (PDF/DOCX with known media types; other files as octet-stream for download)."""
    sid = _parse_session_id(session_id)
    root, channel, path_uid = await _workspace_context(sid)
    target = safe_join_under_session_root(root, path)
    ext = posixpath.splitext(target)[1].lower()
    media_type = _BLOB_MEDIA.get(ext, "application/octet-stream")
    try:
        sb = await _ensure_workspace_sandbox(sid, path_uid, channel)
        data = await sb.fs.read_binary(target)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Blaxel: {e}") from e
    if not isinstance(data, (bytes, bytearray)):
        raise HTTPException(status_code=502, detail="unexpected binary payload")
    body = bytes(data)
    if len(body) > _MAX_BLOB_FILE_BYTES:
        raise HTTPException(status_code=413, detail="file too large for preview")
    filename = (posixpath.basename(target) or "download").replace('"', "'")[:180]
    return Response(
        content=body,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
