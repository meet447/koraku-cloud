"""Persist agent run state so detached runs can resume after worker loss."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from pydantic import BaseModel, Field

from koraku.core.config import settings
from koraku.core.models import SessionState

log = logging.getLogger(__name__)

_memory: dict[str, RunCheckpoint] = {}
_lock = asyncio.Lock()


class RunCheckpoint(BaseModel):
    run_id: str
    owner_sub: str | None = None
    owner_org_id: str | None = None
    session: dict[str, Any] = Field(default_factory=dict)
    step_count: int = 0
    completed: bool = False
    updated_at: float = Field(default_factory=time.time)


def checkpoint_enabled() -> bool:
    return bool(getattr(settings, "run_checkpoint_enabled", True))


def _checkpoint_key(run_id: str, owner_org_id: str | None) -> str:
    org = (owner_org_id or "").strip()
    rid = (run_id or "").strip()
    return f"{org}:{rid}" if org else rid


def _redis_key(run_id: str, owner_org_id: str | None) -> str:
    org = (owner_org_id or "").strip() or "_"
    return f"koraku:{org}:checkpoint:{run_id}"


def _ttl_seconds() -> int:
    return max(60, int(getattr(settings, "run_checkpoint_ttl_seconds", 3600)))


async def save_checkpoint(
    *,
    run_id: str,
    session: SessionState,
    owner_sub: str | None,
    owner_org_id: str | None,
    completed: bool = False,
) -> None:
    if not checkpoint_enabled():
        return
    rid = (run_id or "").strip()
    if not rid:
        return
    cp = RunCheckpoint(
        run_id=rid,
        owner_sub=owner_sub,
        owner_org_id=owner_org_id,
        session=session.model_dump(mode="json"),
        step_count=int(session.step_count),
        completed=completed,
        updated_at=time.time(),
    )
    key = _checkpoint_key(rid, owner_org_id)
    async with _lock:
        _memory[key] = cp
    try:
        from koraku.core.redis_async import get_client

        client = await get_client()
        if client is not None:
            await client.set(
                _redis_key(rid, owner_org_id),
                cp.model_dump_json(),
                ex=_ttl_seconds(),
            )
    except Exception:
        log.debug("checkpoint redis save failed run_id=%s", rid, exc_info=True)


async def load_checkpoint(run_id: str, *, owner_org_id: str | None) -> RunCheckpoint | None:
    if not checkpoint_enabled():
        return None
    rid = (run_id or "").strip()
    if not rid:
        return None
    key = _checkpoint_key(rid, owner_org_id)
    async with _lock:
        mem = _memory.get(key)
    if mem is not None and not mem.completed:
        return mem
    try:
        from koraku.core.redis_async import get_client

        client = await get_client()
        if client is None:
            return None
        raw = await client.get(_redis_key(rid, owner_org_id))
        if not raw:
            return None
        cp = RunCheckpoint.model_validate_json(raw)
        if cp.completed:
            return None
        async with _lock:
            _memory[key] = cp
        return cp
    except Exception:
        log.debug("checkpoint redis load failed run_id=%s", rid, exc_info=True)
        return None


async def mark_checkpoint_completed(run_id: str, *, owner_org_id: str | None) -> None:
    rid = (run_id or "").strip()
    if not rid:
        return
    key = _checkpoint_key(rid, owner_org_id)
    async with _lock:
        cp = _memory.get(key)
        if cp is not None:
            cp.completed = True
    try:
        from koraku.core.redis_async import get_client

        client = await get_client()
        if client is not None:
            await client.delete(_redis_key(rid, owner_org_id))
    except Exception:
        log.debug("checkpoint redis delete failed run_id=%s", rid, exc_info=True)


def restore_session(checkpoint: RunCheckpoint) -> SessionState:
    session = SessionState.model_validate(checkpoint.session)
    session.step_count = int(checkpoint.step_count)
    return session


def reset_checkpoint_store() -> None:
    """Test helper."""
    global _memory
    _memory = {}
