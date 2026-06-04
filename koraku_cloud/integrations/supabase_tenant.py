"""Organization tenancy via Supabase PostgREST (service role)."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from koraku_cloud.automations.supabase_store import _headers, _require_config, _rest_url
from koraku_cloud.integrations.supabase_rest import get_http_client
from koraku.core.config import settings
from koraku.core.tenant import ORG_ID_HEADER
from koraku.core.ttl_cache import TtlCache

log = logging.getLogger(__name__)

_ORG_MEMBERSHIP_CACHE: TtlCache[list[str]] = TtlCache(max_size=512)


def supabase_tenant_configured() -> bool:
    try:
        _require_config()
        return True
    except RuntimeError:
        return False


def ensure_personal_org_sync(user_id: str) -> str | None:
    """Create or return the user's default personal organization id."""
    uid = (user_id or "").strip()
    if not uid:
        return None
    try:
        uuid.UUID(uid)
    except ValueError:
        return None
    if not supabase_tenant_configured():
        return None
    try:
        r = get_http_client().post(
            _rest_url("/rpc/koraku_ensure_personal_org"),
            headers=_headers(),
            json={"p_user_id": uid},
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log.warning("koraku_ensure_personal_org failed user=%s: %s", uid, e)
        return None
    if isinstance(data, str) and data.strip():
        return data.strip()
    return None


def _member_org_ids_sync(user_id: str) -> list[str]:
    uid = (user_id or "").strip()
    if not uid:
        return []
    ttl = max(0.0, float(settings.tenant_org_membership_cache_ttl_seconds))
    if ttl > 0:
        cached = _ORG_MEMBERSHIP_CACHE.get(uid, ttl_seconds=ttl)
        if cached is not None:
            return list(cached)
    q = f"/koraku_org_member?user_id=eq.{uid}&select=org_id,is_default"
    try:
        r = get_http_client().get(_rest_url(q), headers=_headers())
        r.raise_for_status()
        rows = r.json()
    except Exception as e:
        log.warning("org membership list failed user=%s: %s", uid, e)
        return []
    if not isinstance(rows, list):
        return []
    default: list[str] = []
    rest: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        oid = str(row.get("org_id") or "").strip()
        if not oid:
            continue
        if row.get("is_default"):
            default.append(oid)
        else:
            rest.append(oid)
    out = default + rest
    if ttl > 0:
        _ORG_MEMBERSHIP_CACHE.set(uid, out)
    return out


def resolve_org_id_sync(user_id: str, requested_org_id: str | None) -> tuple[str | None, str]:
    """
    Pick an organization the user may act as.

    Returns ``(org_id, reason)`` where reason is ``ok`` or a stable error code.
    """
    uid = (user_id or "").strip()
    if not uid:
        return None, "missing_user"
    req = (requested_org_id or "").strip()
    if req:
        try:
            uuid.UUID(req)
        except ValueError:
            return None, "invalid_org_id"
        members = _member_org_ids_sync(uid)
        if req in members:
            return req, "ok"
        return None, "org_forbidden"

    ensured = ensure_personal_org_sync(uid)
    if ensured:
        return ensured, "ok"
    members = _member_org_ids_sync(uid)
    if members:
        return members[0], "ok"
    return None, "org_unavailable"


def parse_org_header(request_headers: Any) -> str | None:
    raw = request_headers.get(ORG_ID_HEADER) or request_headers.get(ORG_ID_HEADER.upper())
    if raw is None:
        return None
    s = str(raw).strip()
    return s or None
