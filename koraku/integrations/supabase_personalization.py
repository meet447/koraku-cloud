"""Load and save per-user personalization via Supabase PostgREST (service role on the API host)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from koraku.core.config import settings
from koraku.integrations.supabase_rest import get_http_client, headers as rest_headers, rest_url
from koraku.core.ttl_cache import TtlCache
from koraku.integrations.supabase_tenant import ensure_personal_org_sync

log = logging.getLogger(__name__)

_PERSONALIZATION_CACHE: TtlCache[dict[str, str]] = TtlCache(max_size=256)
_EMPTY_PERSONALIZATION = {"agent_name": "", "memory": "", "soul": ""}


def supabase_personalization_configured() -> bool:
    u = (settings.supabase_url or "").strip().rstrip("/")
    k = (settings.supabase_service_role_key or "").strip()
    return bool(u and k)


def _valid_uuid(s: str) -> bool:
    try:
        uuid.UUID((s or "").strip())
    except ValueError:
        return False
    return True


def _cache_key(user_sub: str, org_id: str | None) -> str:
    uid = (user_sub or "").strip()
    oid = (org_id or "").strip()
    return f"{uid}:{oid}" if oid else uid


def invalidate_personalization_cache(user_sub: str | None, *, org_id: str | None = None) -> None:
    uid = (user_sub or "").strip()
    if uid:
        _PERSONALIZATION_CACHE.invalidate(_cache_key(uid, org_id))


def fetch_personalization_sync(user_sub: str, *, org_id: str | None = None) -> dict[str, str] | None:
    """Return ``agent_name``, ``memory``, ``soul`` for ``user_sub``, or ``None`` on transport/HTTP error.

    Missing row returns empty strings for all fields (not ``None``).
    """
    uid = (user_sub or "").strip()
    oid = (org_id or "").strip()
    if not _valid_uuid(uid):
        return None
    if not supabase_personalization_configured():
        return None
    ttl = max(0.0, float(settings.personalization_cache_ttl_seconds))
    ckey = _cache_key(uid, oid or None)
    if ttl > 0:
        cached = _PERSONALIZATION_CACHE.get(ckey, ttl_seconds=ttl)
        if cached is not None:
            return dict(cached)
    if not oid:
        oid = (ensure_personal_org_sync(uid) or "").strip()
    if not oid:
        return dict(_EMPTY_PERSONALIZATION)
    try:
        q = (
            f"/koraku_personalization?user_id=eq.{uid}&org_id=eq.{oid}"
            "&select=agent_name,memory,soul&limit=1"
        )
        r = get_http_client().get(rest_url(q), headers=rest_headers())
        r.raise_for_status()
        rows = r.json()
        if not isinstance(rows, list):
            return None
        if len(rows) == 0:
            out = dict(_EMPTY_PERSONALIZATION)
        else:
            row = rows[0]
            if not isinstance(row, dict):
                out = dict(_EMPTY_PERSONALIZATION)
            else:
                out = {
                    "agent_name": str(row.get("agent_name") or ""),
                    "memory": str(row.get("memory") or ""),
                    "soul": str(row.get("soul") or ""),
                }
        if ttl > 0:
            _PERSONALIZATION_CACHE.set(ckey, out)
        return out
    except Exception as e:
        log.warning("supabase personalization fetch failed: %s", e)
        return None


def upsert_personalization_sync(
    user_sub: str,
    agent_name: str,
    memory: str,
    soul: str,
    *,
    org_id: str | None = None,
) -> None:
    uid = (user_sub or "").strip()
    if not _valid_uuid(uid):
        raise ValueError("invalid user id")
    if not supabase_personalization_configured():
        raise RuntimeError("Supabase not configured for personalization.")
    oid = (org_id or "").strip() or ensure_personal_org_sync(uid)
    if not oid:
        raise ValueError("organization context is required for personalization")
    row: dict[str, Any] = {
        "user_id": uid,
        "org_id": oid,
        "agent_name": (agent_name or "")[:120],
        "memory": memory or "",
        "soul": soul or "",
    }
    payload: list[dict[str, Any]] = [row]
    url = rest_url("/koraku_personalization?on_conflict=user_id,org_id")
    r = get_http_client().post(
        url,
        headers={**rest_headers(), "Prefer": "resolution=merge-duplicates,return=minimal"},
        json=payload,
    )
    r.raise_for_status()
    invalidate_personalization_cache(uid, org_id=oid)
