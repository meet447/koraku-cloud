"""Platform admin authorization (env allowlist + Supabase table)."""
from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import HTTPException, Request

from koraku.core.config import settings
from koraku.core.request_auth import ResolvedRequestAuth, resolve_request_auth

log = logging.getLogger(__name__)


def _env_admin_ids() -> set[str]:
    raw = (getattr(settings, "platform_admin_user_ids", None) or "").strip()
    if not raw:
        return set()
    return {part.strip() for part in raw.split(",") if part.strip()}


def _valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def is_platform_admin_user_id(user_id: str | None) -> bool:
    uid = (user_id or "").strip()
    if not uid or not _valid_uuid(uid):
        return False
    if uid in _env_admin_ids():
        return True
    return _is_platform_admin_in_db_sync(uid)


def _is_platform_admin_in_db_sync(user_id: str) -> bool:
    from koraku_cloud.integrations.supabase_rest import (
        get_http_client,
        headers as rest_headers,
        rest_url,
        supabase_rest_configured,
    )

    if not supabase_rest_configured():
        return False
    try:
        q = f"/koraku_platform_admin?user_id=eq.{user_id}&select=user_id&limit=1"
        r = get_http_client().get(rest_url(q), headers=rest_headers())
        r.raise_for_status()
        rows = r.json()
        return isinstance(rows, list) and len(rows) > 0
    except Exception:
        log.debug("platform admin lookup failed user_id=%s", user_id, exc_info=True)
        return False


async def is_platform_admin_user_id_async(user_id: str | None) -> bool:
    uid = (user_id or "").strip()
    if not uid:
        return False
    if uid in _env_admin_ids():
        return True
    return await asyncio.to_thread(_is_platform_admin_in_db_sync, uid)


def require_platform_admin(request: Request) -> ResolvedRequestAuth:
    resolved = resolve_request_auth(request)
    if not resolved.auth_ok or not resolved.sub:
        raise HTTPException(status_code=401, detail="Authentication required.")
    if resolved.auth.reason != "ok":
        raise HTTPException(status_code=401, detail="Invalid session.")
    if not is_platform_admin_user_id(resolved.sub):
        raise HTTPException(status_code=403, detail="Platform admin access required.")
    return resolved
