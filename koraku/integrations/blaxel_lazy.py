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
    resolve_blaxel_session_root,
)
from koraku.integrations.cloud_user import effective_cloud_user_id

log = logging.getLogger(__name__)

_lazy_session_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "koraku_lazy_blaxel_session",
    default=None,
)
_lazy_session_root: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "koraku_lazy_blaxel_session_root",
    default=None,
)
_ensure_locks: dict[str, asyncio.Lock] = {}


def set_lazy_blaxel_session(
    session_id: str | None,
    *,
    session_root: str | None = None,
) -> tuple[contextvars.Token[str | None] | None, contextvars.Token[str | None] | None]:
    sid_tok: contextvars.Token[str | None] | None = None
    root_tok: contextvars.Token[str | None] | None = None
    if (session_id or "").strip():
        sid_tok = _lazy_session_id.set(session_id.strip())
    if (session_root or "").strip():
        root_tok = _lazy_session_root.set(session_root.strip())
    return sid_tok, root_tok


def clear_lazy_blaxel_session(
    session_token: contextvars.Token[str | None] | None,
    root_token: contextvars.Token[str | None] | None = None,
) -> None:
    if session_token is not None:
        _lazy_session_id.reset(session_token)
    if root_token is not None:
        _lazy_session_root.reset(root_token)


def lazy_blaxel_session_active() -> bool:
    return bool((_lazy_session_id.get() or "").strip())


def _lock_for_user() -> asyncio.Lock:
    key = effective_cloud_user_id()
    lock = _ensure_locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _ensure_locks[key] = lock
    return lock


async def warm_blaxel_session_background() -> None:
    """If this user already has a cached VM, attach it without blocking chat startup."""
    if cloud_blaxel_block_reason(settings):
        return
    if get_active_blaxel_sandbox() is not None:
        return
    if not (_lazy_session_id.get() or "").strip():
        return
    try:
        await ensure_blaxel_for_file_tool()
    except Exception as e:
        log.debug("background Blaxel warm skipped: %s", e)


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
    override = (_lazy_session_root.get() or "").strip() or None
    session_root = resolve_blaxel_session_root(
        sid,
        settings,
        user_id=uid,
        override_root=override,
    )
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
