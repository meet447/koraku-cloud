"""Platform admin queries and mutations (service role)."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from koraku.credits.store import ensure_period_sync, fetch_activity_sync, _row_to_summary
from koraku_cloud.integrations.supabase_rest import (
    get_http_client,
    headers as rest_headers,
    rest_url,
    supabase_rest_configured,
)

log = logging.getLogger(__name__)


def _valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def _audit_log(
    *,
    actor_user_id: str,
    action: str,
    target_type: str,
    target_id: str,
    payload: dict[str, Any] | None = None,
) -> None:
    if not supabase_rest_configured():
        return
    row = {
        "actor_user_id": actor_user_id,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "payload": payload or {},
    }
    try:
        r = get_http_client().post(
            rest_url("/koraku_admin_audit_log"),
            headers={**rest_headers(), "Prefer": "return=minimal"},
            json=[row],
        )
        r.raise_for_status()
    except Exception:
        log.exception("admin audit log failed action=%s target=%s", action, target_id)


def fetch_dashboard_stats_sync() -> dict[str, Any] | None:
    if not supabase_rest_configured():
        return None
    try:
        r = get_http_client().post(
            rest_url("/rpc/koraku_admin_dashboard_stats"),
            headers=rest_headers(),
            json={},
        )
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, dict) else None
    except Exception:
        log.exception("koraku_admin_dashboard_stats failed")
        return None


def search_orgs_sync(query: str, *, limit: int = 25) -> list[dict[str, Any]]:
    if not supabase_rest_configured():
        return []
    q = (query or "").strip()
    if not q:
        return []
    lim = max(1, min(int(limit), 50))
    try:
        r = get_http_client().post(
            rest_url("/rpc/koraku_admin_search_orgs"),
            headers=rest_headers(),
            json={"p_query": q, "p_limit": lim},
        )
        r.raise_for_status()
        rows = r.json()
        if not isinstance(rows, list):
            return []
        out: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            item = {
                "id": row.get("id"),
                "name": row.get("name"),
                "kind": row.get("kind"),
                "created_at": row.get("created_at"),
            }
            if row.get("matched_email"):
                item["matched_email"] = row.get("matched_email")
                item["matched_user_id"] = row.get("matched_user_id")
                item["member_role"] = row.get("member_role")
            out.append(item)
        return out
    except Exception:
        log.exception("search_orgs_sync failed q=%s", q)
        return []


def fetch_org_members_sync(org_id: str) -> list[dict[str, Any]]:
    if not supabase_rest_configured() or not _valid_uuid(org_id):
        return []
    try:
        q = (
            f"/koraku_org_member?org_id=eq.{org_id}"
            "&select=user_id,role,is_default,created_at"
            "&order=created_at.asc"
        )
        r = get_http_client().get(rest_url(q), headers=rest_headers())
        r.raise_for_status()
        rows = r.json()
        return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
    except Exception:
        log.exception("fetch_org_members_sync failed org_id=%s", org_id)
        return []


def fetch_org_admin_state_sync(org_id: str) -> dict[str, Any] | None:
    if not supabase_rest_configured() or not _valid_uuid(org_id):
        return None
    try:
        q = f"/koraku_org_admin_state?org_id=eq.{org_id}&select=*&limit=1"
        r = get_http_client().get(rest_url(q), headers=rest_headers())
        r.raise_for_status()
        rows = r.json()
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            return rows[0]
        return {"org_id": org_id, "suspended": False, "suspend_reason": "", "notes": ""}
    except Exception:
        log.exception("fetch_org_admin_state_sync failed org_id=%s", org_id)
        return None


def fetch_org_detail_sync(org_id: str) -> dict[str, Any] | None:
    if not supabase_rest_configured() or not _valid_uuid(org_id):
        return None
    try:
        q = f"/koraku_organization?id=eq.{org_id}&select=id,name,kind,created_at&limit=1"
        r = get_http_client().get(rest_url(q), headers=rest_headers())
        r.raise_for_status()
        rows = r.json()
        if not isinstance(rows, list) or not rows:
            return None
        org = rows[0]
        period = ensure_period_sync(org_id)
        summary = _row_to_summary(period) if period else None
        members = fetch_org_members_sync(org_id)
        admin_state = fetch_org_admin_state_sync(org_id)
        counts = _fetch_org_counts_sync(org_id)
        activity = fetch_activity_sync(org_id, days=30)
        return {
            "org": org,
            "usage": {
                "plan": summary.plan if summary else "free",
                "credits_limit": summary.credits_limit if summary else 0,
                "credits_used": summary.credits_used if summary else 0,
                "credits_remaining": summary.credits_remaining if summary else 0,
                "percent_used": summary.percent_used if summary else 0.0,
                "period_start": summary.period_start if summary else "",
                "period_end": summary.period_end if summary else "",
                "resets_in_days": summary.resets_in_days if summary else 0,
            },
            "members": members,
            "admin_state": admin_state,
            "counts": counts,
            "activity": activity,
        }
    except Exception:
        log.exception("fetch_org_detail_sync failed org_id=%s", org_id)
        return None


def _fetch_org_counts_sync(org_id: str) -> dict[str, int]:
    counts = {
        "chat_threads": 0,
        "automations": 0,
        "skills": 0,
        "personalization_rows": 0,
    }
    tables = [
        ("chat_threads", "chat_thread", "org_id"),
        ("automations", "koraku_automation", "org_id"),
        ("skills", "koraku_skill", "org_id"),
        ("personalization_rows", "koraku_personalization", "org_id"),
    ]
    headers = {**rest_headers(), "Prefer": "count=exact"}
    for key, table, col in tables:
        try:
            q = f"/{table}?{col}=eq.{org_id}&select={col}&limit=1"
            r = get_http_client().head(rest_url(q), headers=headers)
            content_range = r.headers.get("content-range") or ""
            if "/" in content_range:
                total = content_range.split("/")[-1]
                if total.isdigit():
                    counts[key] = int(total)
        except Exception:
            log.debug("count %s failed org_id=%s", table, org_id, exc_info=True)
    return counts


def fetch_org_ledger_sync(org_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
    if not supabase_rest_configured() or not _valid_uuid(org_id):
        return []
    period = ensure_period_sync(org_id)
    if not period:
        return []
    pstart = period.get("period_start")
    lim = max(1, min(int(limit), 200))
    try:
        q = (
            f"/koraku_usage_ledger?org_id=eq.{org_id}"
            f"&period_start=eq.{pstart}"
            "&select=id,credits,kind,metadata,created_at,idempotency_key"
            f"&order=created_at.desc&limit={lim}"
        )
        r = get_http_client().get(rest_url(q), headers=rest_headers())
        r.raise_for_status()
        rows = r.json()
        return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
    except Exception:
        log.exception("fetch_org_ledger_sync failed org_id=%s", org_id)
        return []


def grant_org_credits_sync(
    org_id: str,
    *,
    grant_credits: int,
    reason: str,
    actor_user_id: str,
    idempotency_key: str,
) -> dict[str, Any] | None:
    if not supabase_rest_configured() or not _valid_uuid(org_id):
        return None
    amount = int(grant_credits)
    if amount <= 0:
        raise ValueError("grant_credits must be positive")
    try:
        r = get_http_client().post(
            rest_url("/rpc/koraku_credit_adjust"),
            headers=rest_headers(),
            json={
                "p_org_id": org_id,
                "p_grant_credits": amount,
                "p_reason": (reason or "").strip() or "admin grant",
                "p_actor_user_id": actor_user_id,
                "p_idempotency_key": idempotency_key,
            },
        )
        r.raise_for_status()
        rows = r.json()
        row = rows[0] if isinstance(rows, list) and rows else {}
        period = ensure_period_sync(org_id)
        result = {
            "settled": bool(row.get("settled")),
            "credits_granted": amount if row.get("settled") else 0,
            "credits_used": row.get("credits_used"),
            "credits_limit": row.get("credits_limit"),
            "period_end": row.get("period_end"),
        }
        _audit_log(
            actor_user_id=actor_user_id,
            action="credits.grant",
            target_type="org",
            target_id=org_id,
            payload={"grant_credits": amount, "reason": reason, "result": result},
        )
        return result
    except Exception as e:
        log.exception("grant_org_credits_sync failed org_id=%s", org_id)
        raise RuntimeError(str(e)) from e


def update_org_period_sync(
    org_id: str,
    *,
    credits_limit: int | None,
    plan: str | None,
    actor_user_id: str,
) -> dict[str, Any] | None:
    if not supabase_rest_configured() or not _valid_uuid(org_id):
        return None
    period = ensure_period_sync(org_id)
    if not period:
        return None
    pstart = period.get("period_start")
    patch: dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if credits_limit is not None:
        lim = int(credits_limit)
        if lim <= 0:
            raise ValueError("credits_limit must be positive")
        patch["credits_limit"] = lim
    if plan is not None:
        p = (plan or "").strip().lower()
        if p not in ("free", "pro", "team"):
            raise ValueError("plan must be free, pro, or team")
        patch["plan"] = p
    if len(patch) <= 1:
        return period
    try:
        q = f"/koraku_usage_period?org_id=eq.{org_id}&period_start=eq.{pstart}"
        r = get_http_client().patch(
            rest_url(q),
            headers={**rest_headers(), "Prefer": "return=representation"},
            json=patch,
        )
        r.raise_for_status()
        rows = r.json()
        updated = rows[0] if isinstance(rows, list) and rows else period
        _audit_log(
            actor_user_id=actor_user_id,
            action="credits.update_period",
            target_type="org",
            target_id=org_id,
            payload={"patch": patch, "period_start": pstart},
        )
        return updated if isinstance(updated, dict) else period
    except Exception as e:
        log.exception("update_org_period_sync failed org_id=%s", org_id)
        raise RuntimeError(str(e)) from e


def update_org_admin_state_sync(
    org_id: str,
    *,
    suspended: bool | None,
    suspend_reason: str | None,
    notes: str | None,
    actor_user_id: str,
) -> dict[str, Any] | None:
    if not supabase_rest_configured() or not _valid_uuid(org_id):
        return None
    row = {
        "org_id": org_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if suspended is not None:
        row["suspended"] = bool(suspended)
    if suspend_reason is not None:
        row["suspend_reason"] = (suspend_reason or "")[:500]
    if notes is not None:
        row["notes"] = (notes or "")[:2000]
    try:
        r = get_http_client().post(
            rest_url("/koraku_org_admin_state?on_conflict=org_id"),
            headers={**rest_headers(), "Prefer": "resolution=merge-duplicates,return=representation"},
            json=[row],
        )
        r.raise_for_status()
        rows = r.json()
        out = rows[0] if isinstance(rows, list) and rows else row
        _audit_log(
            actor_user_id=actor_user_id,
            action="org.update_admin_state",
            target_type="org",
            target_id=org_id,
            payload=row,
        )
        return out if isinstance(out, dict) else row
    except Exception as e:
        log.exception("update_org_admin_state_sync failed org_id=%s", org_id)
        raise RuntimeError(str(e)) from e


def fetch_audit_log_sync(*, limit: int = 50) -> list[dict[str, Any]]:
    if not supabase_rest_configured():
        return []
    lim = max(1, min(int(limit), 200))
    try:
        q = (
            "/koraku_admin_audit_log"
            "?select=id,actor_user_id,action,target_type,target_id,payload,created_at"
            f"&order=created_at.desc&limit={lim}"
        )
        r = get_http_client().get(rest_url(q), headers=rest_headers())
        r.raise_for_status()
        rows = r.json()
        return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
    except Exception:
        log.exception("fetch_audit_log_sync failed")
        return []
