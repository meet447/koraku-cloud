"""Org-scoped agent skills in Supabase (Koraku Cloud)."""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, TypedDict

from koraku.core.ttl_cache import TtlCache
from koraku_cloud.integrations.supabase_rest import (
    get_http_client,
    headers as rest_headers,
    rest_url,
    supabase_rest_configured,
)
from koraku_cloud.integrations.supabase_tenant import ensure_personal_org_sync

log = logging.getLogger(__name__)

_SKILLS_CACHE: TtlCache[list[dict[str, str]]] = TtlCache(max_size=256)


class OrgSkillRow(TypedDict):
    slug: str
    name: str
    description: str
    body: str
    enabled: bool


def supabase_skills_configured() -> bool:
    return supabase_rest_configured()


def _valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def _cache_key(org_id: str) -> str:
    return f"skills:{org_id}"


def invalidate_skills_cache(*, org_id: str | None) -> None:
    oid = (org_id or "").strip()
    if oid:
        _SKILLS_CACHE.invalidate(_cache_key(oid))


def _normalize_slug(raw: str) -> str:
    slug = (raw or "").strip().lower()
    if not slug or len(slug) > 64:
        raise ValueError("slug must be 1–64 characters")
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-")
    if slug[0] not in "abcdefghijklmnopqrstuvwxyz0123456789":
        raise ValueError("slug must start with a letter or digit")
    if any(ch not in allowed for ch in slug):
        raise ValueError("slug may only contain lowercase letters, digits, and hyphens")
    return slug


def _row_to_skill(row: dict[str, Any]) -> OrgSkillRow:
    return {
        "slug": str(row.get("slug") or "").strip(),
        "name": str(row.get("name") or "").strip(),
        "description": str(row.get("description") or "").strip(),
        "body": str(row.get("body") or ""),
        "enabled": bool(row.get("enabled", True)),
    }


def fetch_org_skills_sync(
    user_sub: str,
    *,
    org_id: str | None = None,
    enabled_only: bool = True,
) -> list[OrgSkillRow] | None:
    uid = (user_sub or "").strip()
    if not _valid_uuid(uid):
        return None
    if not supabase_skills_configured():
        return None
    oid = (org_id or "").strip() or (ensure_personal_org_sync(uid) or "").strip()
    if not oid:
        return []

    from koraku.core.config import settings

    ttl = float(getattr(settings, "skills_cache_ttl_seconds", 60))
    ckey = _cache_key(oid)
    if ttl >= 0:
        cached = _SKILLS_CACHE.get(ckey, ttl_seconds=ttl)
        if cached is not None:
            return [_row_to_skill(row) for row in cached]

    try:
        q = (
            f"/koraku_skill?org_id=eq.{oid}"
            "&select=slug,name,description,body,enabled"
            "&order=slug.asc"
        )
        if enabled_only:
            q += "&enabled=eq.true"
        r = get_http_client().get(rest_url(q), headers=rest_headers())
        r.raise_for_status()
        rows = r.json()
        if not isinstance(rows, list):
            return None
        out = [_row_to_skill(row) for row in rows if isinstance(row, dict)]
        if ttl >= 0:
            _SKILLS_CACHE.set(ckey, [dict(skill) for skill in out])
        return out
    except Exception as e:
        log.warning("supabase skills fetch failed: %s", e)
        return None


async def fetch_org_skills_async(
    user_sub: str,
    *,
    org_id: str | None = None,
    enabled_only: bool = True,
) -> list[OrgSkillRow] | None:
    return await asyncio.to_thread(
        fetch_org_skills_sync,
        user_sub,
        org_id=org_id,
        enabled_only=enabled_only,
    )


def upsert_org_skill_sync(
    user_sub: str,
    *,
    org_id: str | None,
    slug: str,
    name: str,
    description: str,
    body: str,
    enabled: bool = True,
) -> None:
    uid = (user_sub or "").strip()
    if not _valid_uuid(uid):
        raise ValueError("invalid user id")
    if not supabase_skills_configured():
        raise RuntimeError("Supabase not configured for skills.")
    oid = (org_id or "").strip() or ensure_personal_org_sync(uid)
    if not oid:
        raise ValueError("organization context is required for skills")
    normalized = _normalize_slug(slug)
    row = {
        "org_id": oid,
        "slug": normalized,
        "name": (name or "")[:120],
        "description": (description or "")[:1024],
        "body": body or "",
        "enabled": bool(enabled),
    }
    url = rest_url("/koraku_skill?on_conflict=org_id,slug")
    r = get_http_client().post(
        url,
        headers={**rest_headers(), "Prefer": "resolution=merge-duplicates,return=minimal"},
        json=[row],
    )
    r.raise_for_status()
    invalidate_skills_cache(org_id=oid)


def delete_org_skill_sync(
    user_sub: str,
    *,
    org_id: str | None,
    slug: str,
) -> None:
    uid = (user_sub or "").strip()
    if not _valid_uuid(uid):
        raise ValueError("invalid user id")
    if not supabase_skills_configured():
        raise RuntimeError("Supabase not configured for skills.")
    oid = (org_id or "").strip() or ensure_personal_org_sync(uid)
    if not oid:
        raise ValueError("organization context is required for skills")
    normalized = _normalize_slug(slug)
    q = f"/koraku_skill?org_id=eq.{oid}&slug=eq.{normalized}"
    r = get_http_client().delete(rest_url(q), headers=rest_headers())
    r.raise_for_status()
    invalidate_skills_cache(org_id=oid)
