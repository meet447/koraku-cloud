"""Load and save per-user personalization via Supabase PostgREST (service role on the API host)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import httpx

from koraku.core.config import settings
from koraku.core.ttl_cache import TtlCache
from koraku.integrations.supabase_tenant import ensure_personal_org_sync

log = logging.getLogger(__name__)

_PERSONALIZATION_CACHE: TtlCache[dict[str, str]] = TtlCache(max_size=256)
_EMPTY_PERSONALIZATION = {"agent_name": "", "memory": "", "soul": ""}


def supabase_personalization_configured() -> bool:
    u = (settings.supabase_url or "").strip().rstrip("/")
    k = (settings.supabase_service_role_key or "").strip()
    return bool(u and k)


def _require_rest() -> tuple[str, str]:
    u = (settings.supabase_url or "").strip().rstrip("/")
    k = (settings.supabase_service_role_key or "").strip()
    if not u or not k:
        raise RuntimeError("Supabase URL and service role key required for personalization.")
    return u, k


def _headers() -> dict[str, str]:
    _, key = _require_rest()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _rest_url(path: str) -> str:
    base, _ = _require_rest()
    return f"{base}/rest/v1{path}"


def _valid_uuid(s: str) -> bool:
    try:
        uuid.UUID((s or "").strip())
    except ValueError:
        return False
    return True


def invalidate_personalization_cache(user_sub: str | None) -> None:
    uid = (user_sub or "").strip()
    if uid:
        _PERSONALIZATION_CACHE.invalidate(uid)


def fetch_personalization_sync(user_sub: str) -> dict[str, str] | None:
    """Return ``agent_name``, ``memory``, ``soul`` for ``user_sub``, or ``None`` on transport/HTTP error.

    Missing row returns empty strings for all fields (not ``None``).
    """
    uid = (user_sub or "").strip()
    if not _valid_uuid(uid):
        return None
    if not supabase_personalization_configured():
        return None
    ttl = max(0.0, float(settings.personalization_cache_ttl_seconds))
    if ttl > 0:
        cached = _PERSONALIZATION_CACHE.get(uid, ttl_seconds=ttl)
        if cached is not None:
            return dict(cached)
    try:
        with httpx.Client(timeout=30.0) as client:
            q = f"/koraku_personalization?user_id=eq.{uid}&select=agent_name,memory,soul&limit=1"
            r = client.get(_rest_url(q), headers=_headers())
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
                _PERSONALIZATION_CACHE.set(uid, out)
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
    row: dict[str, Any] = {
        "user_id": uid,
        "agent_name": (agent_name or "")[:120],
        "memory": memory or "",
        "soul": soul or "",
    }
    if oid:
        row["org_id"] = oid
    payload: list[dict[str, Any]] = [row]
    with httpx.Client(timeout=30.0) as client:
        url = _rest_url("/koraku_personalization?on_conflict=user_id")
        r = client.post(
            url,
            headers={**_headers(), "Prefer": "resolution=merge-duplicates,return=minimal"},
            json=payload,
        )
        r.raise_for_status()
    invalidate_personalization_cache(uid)
