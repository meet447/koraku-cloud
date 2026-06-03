"""Blaxel sandboxes for ``execution_target=cloud`` (isolated file + shell tools)."""
from __future__ import annotations

import logging
import posixpath
import re
import shlex
import time
from typing import TYPE_CHECKING, Any

from koraku.core.config import Settings, settings
from koraku.integrations.cloud_user import (
    auth_user_id_from_storage_scope,
    effective_cloud_user_id,
    workspace_path_user_id,
)

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)

# Per-user VM handle cache (avoids repeated ``create_if_not_exists`` on follow-up turns).
_sandbox_cache: dict[str, tuple[Any, float]] = {}

_BLAXEL_AUTH_HELP = (
    "Blaxel rejected these credentials. Create a long-lived API key at "
    "https://app.blaxel.ai/profile/security and set BL_API_KEY in the server .env (single line, "
    "no quotes or trailing spaces). Set BL_WORKSPACE to the workspace slug from your browser URL "
    "https://app.blaxel.ai/<slug> — the key must belong to that workspace. Restart the API after "
    "changing .env."
)


def _blaxel_error_looks_like_auth_failure(exc: BaseException) -> bool:
    """HTTP 401/403 or common auth phrases from Blaxel / httpx."""
    parts: list[str] = [f"{type(exc).__name__} {exc}".lower()]
    resp = getattr(exc, "response", None)
    if resp is not None:
        sc = getattr(resp, "status_code", None)
        if sc in (401, 403):
            return True
        try:
            txt = getattr(resp, "text", "") or ""
            if isinstance(txt, str):
                parts.append(txt.lower())
        except Exception:
            pass
    cause = exc.__cause__
    if isinstance(cause, BaseException):
        parts.append(f"{type(cause).__name__} {cause}".lower())
    combined = " ".join(parts)
    return any(
        m in combined
        for m in (
            "authorization",
            "401",
            "403",
            "unauthorized",
            "forbidden",
            "invalid token",
            "authentication",
            "access denied",
        )
    )


try:
    from blaxel.core import SandboxInstance as _SandboxInstance  # type: ignore import-not-found

    _BLAXEL_IMPORT_ERROR: Exception | None = None
except Exception as e:  # pragma: no cover - optional dependency
    _SandboxInstance = None
    _BLAXEL_IMPORT_ERROR = e


def blaxel_sdk_available() -> bool:
    return _SandboxInstance is not None


def blaxel_import_error_message() -> str | None:
    if _BLAXEL_IMPORT_ERROR is None:
        return None
    return str(_BLAXEL_IMPORT_ERROR)


def blaxel_credentials_configured(settings: Settings) -> bool:
    return bool((settings.bl_workspace or "").strip() and (settings.bl_api_key or "").strip())


def cloud_blaxel_block_reason(settings: Settings) -> str | None:
    """If set, **Sandbox** (Blaxel) in the OSS UI cannot start — do not fall back to the host repo."""
    if not settings.blaxel_cloud_sandbox_enabled:
        return (
            "Sandbox mode uses a Blaxel VM only. Set BLAXEL_CLOUD_SANDBOX_ENABLED=true on the "
            "Koraku backend, plus BL_WORKSPACE and BL_API_KEY (see .env.example)."
        )
    if not blaxel_sdk_available():
        ie = blaxel_import_error_message() or "unknown import error"
        return (
            "Sandbox mode needs the `blaxel` package in the Python that runs this API. "
            "If you use a venv, start Koraku with that interpreter (e.g. `.venv/bin/python main.py`) "
            "or run `pip install blaxel` for the same `python` your server uses. "
            f"Import error: {ie}"
        )
    if not (settings.bl_api_key or "").strip():
        return "Sandbox mode requires BL_API_KEY in the server's environment (.env)."
    if not (settings.bl_workspace or "").strip():
        return (
            "Sandbox mode requires BL_WORKSPACE in the server's .env — the workspace slug from "
            "https://app.blaxel.ai/<workspace> in your browser."
        )
    return None


def user_sandbox_name(user_id: str) -> str:
    """Stable DNS-safe Blaxel VM name (one sandbox per user)."""
    raw = (user_id or "").strip()
    safe = re.sub(r"[^a-zA-Z0-9]+", "", raw)[:32]
    if not safe:
        safe = "user"
    return f"koraku-user-{safe}"


def _path_segment_user(user_id: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_.-]+", "-", (user_id or "").strip())[:64]
    return s or "user"


def _path_segment_session(session_id: str) -> str:
    raw = (session_id or "").strip()
    try:
        import uuid as _uuid

        _uuid.UUID(raw)
        return raw
    except ValueError:
        safe = re.sub(r"[^a-zA-Z0-9-]+", "-", raw)[:64]
        return safe or "session"


def _koraku_workdir_base(settings: Settings) -> str:
    return (settings.blaxel_sandbox_workdir or "/tmp").strip().replace("\\", "/").rstrip("/") or "/tmp"


def session_workspace_root_posix(user_id: str, session_id: str, settings: Settings) -> str:
    """Per-chat folder inside the VM: ``{workdir}/koraku/users/{user}/sessions/{session}/``."""
    base = _koraku_workdir_base(settings)
    uid = _path_segment_user(user_id)
    sid = _path_segment_session(session_id)
    return posixpath.join(base, "koraku", "users", uid, "sessions", sid)


def imessage_workspace_root_posix(user_id: str, thread_id: str, settings: Settings) -> str:
    """Dedicated iMessage folder (separate from web chat sessions): ``.../users/{user}/imessage/{thread}/``."""
    base = _koraku_workdir_base(settings)
    uid = _path_segment_user(user_id)
    tid = _path_segment_session(thread_id)
    return posixpath.join(base, "koraku", "users", uid, "imessage", tid)


def resolve_blaxel_session_root(
    session_id: str,
    settings: Settings,
    *,
    user_id: str | None = None,
    override_root: str | None = None,
) -> str:
    """POSIX workspace root for file tools this turn."""
    if (override_root or "").strip():
        return override_root.strip()
    uid = (user_id or effective_cloud_user_id()).strip() or effective_cloud_user_id()
    return session_workspace_root_posix(uid, session_id, settings)


async def _mkdir_p_in_sandbox(sb: Any, session_root: str, settings: Settings) -> None:
    wd = (settings.blaxel_sandbox_workdir or "/tmp").strip().replace("\\", "/").rstrip("/") or "/tmp"
    cmd = f"mkdir -p {shlex.quote(session_root)}"
    try:
        await sb.process.exec(
            {
                "command": cmd,
                "working_dir": wd,
                "wait_for_completion": True,
                "timeout": 60,
            }
        )
    except Exception:
        log.exception("Blaxel mkdir -p failed path=%s wd=%s", session_root, wd)


async def _ensure_user_blaxel_vm(
    user_id: str,
    *,
    label_session: str,
    settings: Settings,
) -> Any:
    """Create or resume the per-user Blaxel VM (shared by web chat and iMessage)."""
    if _SandboxInstance is None:
        raise RuntimeError(
            "blaxel package is not installed. Add `blaxel` to the environment (see requirements.txt)."
        )
    if not blaxel_credentials_configured(settings):
        raise RuntimeError("Set BL_WORKSPACE and BL_API_KEY for Blaxel sandboxes.")

    uid = (user_id or effective_cloud_user_id()).strip() or effective_cloud_user_id()
    name = user_sandbox_name(uid)
    spec: dict[str, Any] = {
        "name": name,
        "image": settings.blaxel_sandbox_image,
        "memory": int(settings.blaxel_sandbox_memory_mb),
        "region": settings.blaxel_sandbox_region,
        "labels": {
            "app": "koraku",
            "koraku_user": uid[:48],
            "koraku_session": (label_session or "")[:36],
        },
    }
    log.info(
        "Blaxel sandbox ensure name=%s user=%s label_session=%s",
        name,
        uid,
        label_session[:12] if label_session else "",
    )
    ttl = max(60.0, float(getattr(settings, "blaxel_sandbox_cache_ttl_seconds", 600.0)))
    now = time.monotonic()
    cached = _sandbox_cache.get(name)
    if cached is not None and (now - cached[1]) < ttl:
        return cached[0]
    try:
        sb = await _SandboxInstance.create_if_not_exists(spec)
    except Exception as e:
        if _blaxel_error_looks_like_auth_failure(e):
            raise RuntimeError(_BLAXEL_AUTH_HELP) from e
        raise
    _sandbox_cache[name] = (sb, now)
    return sb


async def ensure_chat_sandbox(
    session_id: str,
    settings: Settings,
    *,
    user_id: str | None = None,
) -> Any:
    """Create or resume the user's Blaxel VM and ensure this chat's session directory exists."""
    uid = (user_id or effective_cloud_user_id()).strip() or effective_cloud_user_id()
    sb = await _ensure_user_blaxel_vm(uid, label_session=session_id, settings=settings)
    root = session_workspace_root_posix(uid, session_id, settings)
    await _mkdir_p_in_sandbox(sb, root, settings)
    return sb


async def ensure_imessage_sandbox(
    thread_id: str,
    settings: Settings,
    *,
    user_id: str | None = None,
) -> tuple[Any, str]:
    """Ensure the user's VM and a dedicated iMessage workspace folder for this thread."""
    uid = (user_id or effective_cloud_user_id()).strip() or effective_cloud_user_id()
    tid = (thread_id or "").strip()
    if not tid:
        raise ValueError("thread_id required for iMessage sandbox")
    label = f"imessage-{tid[:12]}"
    sb = await _ensure_user_blaxel_vm(uid, label_session=label, settings=settings)
    root = imessage_workspace_root_posix(uid, tid, settings)
    await _mkdir_p_in_sandbox(sb, root, settings)
    return sb, root


def workspace_root_posix_for_channel(
    user_id: str,
    session_id: str,
    channel: str,
    settings: Settings,
) -> str:
    """Blaxel path for a thread — web chats use ``sessions/``, iMessage uses ``imessage/``."""
    if (channel or "").strip().lower() == "imessage":
        return imessage_workspace_root_posix(user_id, session_id, settings)
    return session_workspace_root_posix(user_id, session_id, settings)


async def ensure_session_workspace(
    session_id: str,
    settings: Settings,
    *,
    user_id: str | None = None,
    channel: str | None = None,
) -> tuple[Any, str]:
    """Attach VM + mkdir for the correct per-thread folder (web or iMessage)."""
    from koraku.integrations.supabase_external import resolve_thread_channel_sync

    scope_uid = (user_id or effective_cloud_user_id()).strip() or effective_cloud_user_id()
    sid = (session_id or "").strip()
    if not sid:
        raise ValueError("session_id required")
    auth_uid = auth_user_id_from_storage_scope(scope_uid)
    ch = (channel or "").strip().lower() or resolve_thread_channel_sync(sid, auth_uid)
    path_uid = workspace_path_user_id(scope_uid, ch)
    if ch == "imessage":
        return await ensure_imessage_sandbox(sid, settings, user_id=path_uid)
    sb = await ensure_chat_sandbox(sid, settings, user_id=path_uid)
    root = session_workspace_root_posix(path_uid, sid, settings)
    return sb, root


def get_cached_user_sandbox(user_id: str | None = None) -> Any | None:
    """Return a warm Blaxel VM handle for this user, if still within the cache TTL."""
    uid = (user_id or effective_cloud_user_id()).strip() or effective_cloud_user_id()
    name = user_sandbox_name(uid)
    cached = _sandbox_cache.get(name)
    if cached is None:
        return None
    ttl = max(60.0, float(getattr(settings, "blaxel_sandbox_cache_ttl_seconds", 600.0)))
    if (time.monotonic() - cached[1]) >= ttl:
        _sandbox_cache.pop(name, None)
        return None
    return cached[0]


def user_sandbox_is_cached(user_id: str | None = None) -> bool:
    return get_cached_user_sandbox(user_id) is not None
