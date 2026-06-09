"""Supabase persistence for org credit periods and ledger."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from koraku.core.config import settings

log = logging.getLogger(__name__)


def _rest():
    from koraku_cloud.integrations.supabase_rest import (
        get_http_client,
        headers as rest_headers,
        rest_url,
        supabase_rest_configured,
    )

    return get_http_client, rest_headers, rest_url, supabase_rest_configured


@dataclass(frozen=True)
class UsageSummary:
    plan: str
    credits_limit: int
    credits_used: int
    period_start: str
    period_end: str
    percent_used: float
    resets_in_days: int

    @property
    def credits_remaining(self) -> int:
        return max(0, self.credits_limit - self.credits_used)


def credits_configured() -> bool:
    _, _, _, configured = _rest()
    return configured()


def _default_limit() -> int:
    return max(1, int(settings.credits_free_monthly_limit))


def _min_reserve() -> int:
    return max(0, int(settings.credits_min_reserve))


def ensure_period_sync(org_id: str) -> dict[str, Any] | None:
    if not credits_configured():
        return None
    oid = (org_id or "").strip()
    if not oid:
        return None
    get_http_client, rest_headers, rest_url, _ = _rest()
    try:
        r = get_http_client().post(
            rest_url("/rpc/koraku_ensure_usage_period"),
            headers=rest_headers(),
            json={"p_org_id": oid},
        )
        r.raise_for_status()
        row = r.json()
        return row if isinstance(row, dict) else None
    except Exception:
        log.exception("koraku_ensure_usage_period failed org_id=%s", oid)
        return None


def fetch_summary_sync(org_id: str) -> UsageSummary | None:
    row = ensure_period_sync(org_id)
    if not row:
        return None
    return _row_to_summary(row)


def _row_to_summary(row: dict[str, Any]) -> UsageSummary:
    limit = int(row.get("credits_limit") or _default_limit())
    used = int(row.get("credits_used") or 0)
    period_end_raw = row.get("period_end")
    period_end = _parse_ts(period_end_raw)
    now = datetime.now(timezone.utc)
    resets_days = max(0, int((period_end - now).total_seconds() // 86400)) if period_end else 0
    pct = (used / limit * 100.0) if limit > 0 else 0.0
    return UsageSummary(
        plan=str(row.get("plan") or "free"),
        credits_limit=limit,
        credits_used=used,
        period_start=str(row.get("period_start") or ""),
        period_end=period_end.isoformat() if period_end else str(period_end_raw or ""),
        percent_used=round(min(100.0, pct), 2),
        resets_in_days=resets_days,
    )


def _parse_ts(value: Any) -> datetime | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        return datetime.fromisoformat(raw).astimezone(timezone.utc)
    except ValueError:
        return None


def _org_suspended_sync(org_id: str) -> bool:
    oid = (org_id or "").strip()
    if not oid or not credits_configured():
        return False
    get_http_client, rest_headers, rest_url, _ = _rest()
    try:
        q = f"/koraku_org_admin_state?org_id=eq.{oid}&select=suspended&limit=1"
        r = get_http_client().get(rest_url(q), headers=rest_headers())
        r.raise_for_status()
        rows = r.json()
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            return bool(rows[0].get("suspended"))
    except Exception:
        log.debug("org suspend check failed org_id=%s", oid, exc_info=True)
    return False


def pre_check_sync(org_id: str, reserve: int | None = None) -> tuple[bool, UsageSummary | None]:
    """Return (allowed, summary). When credits are not configured, always allowed."""
    if not credits_configured():
        return True, None
    if _org_suspended_sync(org_id):
        return False, fetch_summary_sync(org_id)
    summary = fetch_summary_sync(org_id)
    if summary is None:
        return True, None
    need = reserve if reserve is not None else _min_reserve()
    allowed = summary.credits_used + need <= summary.credits_limit
    return allowed, summary


def settle_sync(
    org_id: str,
    *,
    idempotency_key: str,
    credits: int,
    kind: str,
    metadata: dict[str, Any],
) -> tuple[bool, UsageSummary | None]:
    if not credits_configured() or credits <= 0:
        return False, fetch_summary_sync(org_id)
    oid = (org_id or "").strip()
    key = (idempotency_key or "").strip()
    if not oid or not key:
        return False, None
    get_http_client, rest_headers, rest_url, _ = _rest()
    try:
        r = get_http_client().post(
            rest_url("/rpc/koraku_credit_settle"),
            headers=rest_headers(),
            json={
                "p_org_id": oid,
                "p_idempotency_key": key,
                "p_credits": int(credits),
                "p_kind": kind,
                "p_metadata": metadata,
            },
        )
        r.raise_for_status()
        rows = r.json()
        if not isinstance(rows, list) or not rows:
            return False, fetch_summary_sync(org_id)
        row = rows[0] if isinstance(rows[0], dict) else {}
        period = ensure_period_sync(org_id)
        if period:
            period["credits_used"] = row.get("credits_used", period.get("credits_used"))
            period["credits_limit"] = row.get("credits_limit", period.get("credits_limit"))
            period["period_end"] = row.get("period_end", period.get("period_end"))
            return bool(row.get("settled")), _row_to_summary(period)
        return bool(row.get("settled")), None
    except httpx.HTTPStatusError as exc:
        body = (exc.response.text or "")[:500]
        log.error(
            "koraku_credit_settle failed org_id=%s key=%s status=%s body=%s",
            oid,
            key,
            exc.response.status_code,
            body,
        )
        return False, None
    except Exception:
        log.exception("koraku_credit_settle failed org_id=%s key=%s", oid, key)
        return False, None


def fetch_activity_sync(org_id: str, *, days: int = 30) -> list[dict[str, Any]]:
    if not credits_configured():
        return []
    oid = (org_id or "").strip()
    if not oid:
        return []
    period = ensure_period_sync(org_id)
    if not period:
        return []
    pstart = period.get("period_start")
    window_days = max(1, min(int(days), 90))
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=window_days)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        q = (
            f"/koraku_usage_ledger?org_id=eq.{oid}"
            f"&period_start=eq.{pstart}"
            f"&created_at=gte.{cutoff}"
            "&select=credits,kind,created_at"
            "&order=created_at.desc"
            f"&limit={max(1, min(window_days * 48, 500))}"
        )
        get_http_client, rest_headers, rest_url, _ = _rest()
        r = get_http_client().get(rest_url(q), headers=rest_headers())
        r.raise_for_status()
        rows = r.json()
        return [x for x in rows if isinstance(x, dict)] if isinstance(rows, list) else []
    except Exception:
        log.exception("fetch_activity_sync failed org_id=%s", oid)
        return []
