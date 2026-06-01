"""Lazy Blaxel activation for chat turns that defer sandbox provisioning."""
from __future__ import annotations

import asyncio
import contextvars
import logging

from koraku.agent.blaxel_scope import bind_blaxel_sandbox, get_active_blaxel_sandbox
from koraku.core.config import settings
from koraku.integrations.blaxel_runtime import (
    cloud_blaxel_block_reason,
    ensure_chat_sandbox,
    session_workspace_root_posix,
)
from koraku.integrations.cloud_user import effective_cloud_user_id

log = logging.getLogger(__name__)

_lazy_session_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "koraku_lazy_blaxel_session",
    default=None,
)
_ensure_locks: dict[str, asyncio.Lock] = {}


def set_lazy_blaxel_session(session_id: str | None) -> contextvars.Token[str | None] | None:
    if not (session_id or "").strip():
        return None
    return _lazy_session_id.set(session_id.strip())


def clear_lazy_blaxel_session(token: contextvars.Token[str | None] | None) -> None:
    if token is not None:
        _lazy_session_id.reset(token)


def _lock_for_user() -> asyncio.Lock:
    key = effective_cloud_user_id()
    lock = _ensure_locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _ensure_locks[key] = lock
    return lock


async def ensure_blaxel_for_file_tool() -> bool:
    """Attach Blaxel to the current tool call when chat deferred upfront provisioning."""
    if get_active_blaxel_sandbox() is not None:
        return True
    sid = _lazy_session_id.get()
    if not sid:
        return False
    if cloud_blaxel_block_reason(settings):
        return False
    uid = effective_cloud_user_id()
    session_root = session_workspace_root_posix(uid, sid, settings)
    async with _lock_for_user():
        if get_active_blaxel_sandbox() is not None:
            return True
        try:
            sb = await ensure_chat_sandbox(sid, settings, user_id=uid)
        except Exception as e:
            log.warning("lazy Blaxel ensure failed session=%s: %s", sid[:12], e)
            return False
        bind_blaxel_sandbox(sb, session_root)
        return True
