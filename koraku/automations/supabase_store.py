"""Koraku automations persistence via Supabase PostgREST (service role from the Python API)."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from koraku.integrations import supabase_rest

log = logging.getLogger(__name__)

_UTC = timezone.utc
_TABLE = "koraku_automation"
_RUN_TABLE = "koraku_automation_run"

TriggerMode = Literal["scheduled", "event"]
AutomationStatus = Literal["active", "paused"]

# Re-exported for supabase_tenant and legacy imports.
_require_config = supabase_rest.require_config
_headers = lambda: supabase_rest.headers(prefer_representation=True)
_rest_url = supabase_rest.rest_url


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_UTC)
    return dt.astimezone(_UTC).isoformat()


def supabase_automations_configured() -> bool:
    return supabase_rest.supabase_rest_configured()


def _client():
    return supabase_rest.get_http_client()


def _row_to_automation(o: dict[str, Any]) -> dict[str, Any]:
    tk = o.get("toolkits") or []
    if not isinstance(tk, list):
        tk = []
    return {
        "id": o["id"],
        "user_id": str(o["user_id"]),
        "org_id": str(o.get("org_id") or ""),
        "title": o["title"],
        "headline": (o.get("headline") or o["title"] or ""),
        "natural_language_spec": o["natural_language_spec"],
        "trigger_mode": o["trigger_mode"],
        "status": o["status"],
        "timezone": o.get("timezone"),
        "cron_expression": o.get("cron_expression"),
        "event_display": o.get("event_display"),
        "toolkits": [str(x).strip().upper() for x in tk if str(x).strip()],
        "created_at": o.get("created_at"),
        "updated_at": o.get("updated_at"),
        "last_run_at": o.get("last_run_at"),
        "next_run_at": o.get("next_run_at"),
    }


def _automation_scope(user_id: str, org_id: str, *, automation_id: str | None = None) -> str:
    uid = (user_id or "").strip()
    oid = (org_id or "").strip()
    parts = [f"user_id=eq.{uid}", f"org_id=eq.{oid}"]
    if automation_id:
        parts.insert(0, f"id=eq.{(automation_id or '').strip()}")
    return "&".join(parts)


def list_automations(user_id: str, org_id: str) -> list[dict[str, Any]]:
    uid = (user_id or "").strip()
    oid = (org_id or "").strip()
    q = f"/{_TABLE}?{_automation_scope(uid, oid)}&order=updated_at.desc"
    r = _client().get(_rest_url(q), headers=_headers())
    r.raise_for_status()
    rows = r.json()
    if not isinstance(rows, list):
        return []
    return [_row_to_automation(x) for x in rows if isinstance(x, dict)]


def list_scheduled_active_all_users() -> list[dict[str, Any]]:
    """Rows for APScheduler (service role); each dict includes ``user_id`` and ``org_id``."""
    q = (
        f"/{_TABLE}?trigger_mode=eq.scheduled&status=eq.active"
        "&select=id,user_id,org_id,title,headline,natural_language_spec,trigger_mode,status,"
        "timezone,cron_expression,event_display,toolkits,created_at,updated_at,last_run_at,next_run_at"
    )
    r = _client().get(_rest_url(q), headers=_headers())
    r.raise_for_status()
    rows = r.json()
    if not isinstance(rows, list):
        return []
    return [_row_to_automation(x) for x in rows if isinstance(x, dict)]


def get_automation(
    user_id: str,
    automation_id: str,
    *,
    org_id: str | None = None,
) -> dict[str, Any] | None:
    uid = (user_id or "").strip()
    aid = (automation_id or "").strip()
    oid = (org_id or "").strip()
    if oid:
        q = f"/{_TABLE}?{_automation_scope(uid, oid, automation_id=aid)}&limit=1"
    else:
        q = f"/{_TABLE}?id=eq.{aid}&user_id=eq.{uid}&limit=1"
    r = _client().get(_rest_url(q), headers=_headers())
    r.raise_for_status()
    rows = r.json()
    if not isinstance(rows, list) or not rows:
        return None
    row = rows[0]
    return _row_to_automation(row) if isinstance(row, dict) else None


def insert_automation(
    user_id: str,
    org_id: str,
    *,
    title: str,
    headline: str,
    natural_language_spec: str,
    trigger_mode: TriggerMode,
    status: AutomationStatus,
    timezone: str | None,
    cron_expression: str | None,
    event_display: str | None,
    toolkits: list[str],
) -> dict[str, Any]:
    uid = (user_id or "").strip()
    oid = (org_id or "").strip()
    if not oid:
        raise ValueError("org_id is required to create an automation")
    aid = str(uuid.uuid4())
    now = _iso(datetime.now(_UTC))
    body = {
        "id": aid,
        "user_id": uid,
        "org_id": oid,
        "title": title.strip(),
        "headline": (headline.strip() or title.strip()),
        "natural_language_spec": natural_language_spec.strip(),
        "trigger_mode": trigger_mode,
        "status": status,
        "timezone": timezone,
        "cron_expression": cron_expression,
        "event_display": event_display,
        "toolkits": [t.strip().upper() for t in toolkits if t.strip()],
        "created_at": now,
        "updated_at": now,
    }
    r = _client().post(_rest_url(f"/{_TABLE}"), headers=_headers(), content=json.dumps(body))
    if r.status_code >= 400:
        log.error("insert_automation failed: %s %s", r.status_code, r.text)
    r.raise_for_status()
    rows = r.json()
    if isinstance(rows, list) and rows and isinstance(rows[0], dict):
        return _row_to_automation(rows[0])
    row = get_automation(uid, aid, org_id=oid)
    assert row is not None
    return row


def update_automation(
    user_id: str,
    org_id: str,
    automation_id: str,
    *,
    title: str | None = None,
    headline: str | None = None,
    natural_language_spec: str | None = None,
    status: AutomationStatus | None = None,
    timezone: str | None = None,
    cron_expression: str | None = None,
    event_display: str | None = None,
    toolkits: list[str] | None = None,
) -> dict[str, Any] | None:
    uid = (user_id or "").strip()
    oid = (org_id or "").strip()
    aid = (automation_id or "").strip()
    patch: dict[str, Any] = {"updated_at": _iso(datetime.now(_UTC))}
    if title is not None:
        patch["title"] = title.strip()
    if headline is not None:
        patch["headline"] = headline.strip()
    if natural_language_spec is not None:
        patch["natural_language_spec"] = natural_language_spec.strip()
    if status is not None:
        patch["status"] = status
    if timezone is not None:
        patch["timezone"] = timezone
    if cron_expression is not None:
        patch["cron_expression"] = cron_expression
    if event_display is not None:
        patch["event_display"] = event_display
    if toolkits is not None:
        patch["toolkits"] = [t.strip().upper() for t in toolkits if t.strip()]
    if len(patch) <= 1:
        return get_automation(uid, aid, org_id=oid)
    q = f"/{_TABLE}?{_automation_scope(uid, oid, automation_id=aid)}"
    r = _client().patch(_rest_url(q), headers=_headers(), content=json.dumps(patch))
    if r.status_code == 404 or r.status_code == 406:
        return None
    r.raise_for_status()
    rows = r.json()
    if isinstance(rows, list) and rows and isinstance(rows[0], dict):
        return _row_to_automation(rows[0])
    return get_automation(uid, aid, org_id=oid)


def delete_automation(user_id: str, org_id: str, automation_id: str) -> bool:
    uid = (user_id or "").strip()
    oid = (org_id or "").strip()
    aid = (automation_id or "").strip()
    q = f"/{_TABLE}?{_automation_scope(uid, oid, automation_id=aid)}"
    r = _client().delete(_rest_url(q), headers=_headers())
    if r.status_code == 404:
        return False
    r.raise_for_status()
    return True


def set_automation_run_times(
    user_id: str,
    org_id: str,
    automation_id: str,
    *,
    last_run_at: datetime | None = None,
    next_run_at: datetime | None = None,
) -> None:
    uid = (user_id or "").strip()
    oid = (org_id or "").strip()
    aid = (automation_id or "").strip()
    patch: dict[str, Any] = {"updated_at": _iso(datetime.now(_UTC))}
    if last_run_at is not None:
        patch["last_run_at"] = _iso(last_run_at)
    if next_run_at is not None:
        patch["next_run_at"] = _iso(next_run_at)
    if len(patch) <= 1:
        return
    q = f"/{_TABLE}?{_automation_scope(uid, oid, automation_id=aid)}"
    r = _client().patch(_rest_url(q), headers=_headers(), content=json.dumps(patch))
    r.raise_for_status()


def insert_run_start(
    user_id: str,
    org_id: str,
    automation_id: str,
    *,
    trigger_summary: str,
) -> str:
    uid = (user_id or "").strip()
    oid = (org_id or "").strip()
    aid = (automation_id or "").strip()
    rid = str(uuid.uuid4())
    now = _iso(datetime.now(_UTC))
    body = {
        "id": rid,
        "automation_id": aid,
        "user_id": uid,
        "org_id": oid,
        "status": "running",
        "trigger_summary": trigger_summary[:8000],
        "started_at": now,
    }
    r = _client().post(_rest_url(f"/{_RUN_TABLE}"), headers=_headers(), content=json.dumps(body))
    r.raise_for_status()
    return rid


def finish_run(
    user_id: str,
    org_id: str,
    run_id: str,
    *,
    status: Literal["success", "failed"],
    result_summary: str | None,
    error: str | None,
    started_at: datetime,
    finished_at: datetime,
) -> None:
    uid = (user_id or "").strip()
    oid = (org_id or "").strip()
    rid = (run_id or "").strip()
    duration_ms = int((finished_at - started_at).total_seconds() * 1000)
    patch = {
        "status": status,
        "result_summary": (result_summary or "")[:12000] or None,
        "error": (error or "")[:8000] or None,
        "finished_at": _iso(finished_at),
        "duration_ms": duration_ms,
    }
    q = f"/{_RUN_TABLE}?id=eq.{rid}&user_id=eq.{uid}&org_id=eq.{oid}"
    r = _client().patch(_rest_url(q), headers=_headers(), content=json.dumps(patch))
    r.raise_for_status()


def list_runs(
    user_id: str,
    org_id: str,
    automation_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    uid = (user_id or "").strip()
    oid = (org_id or "").strip()
    aid = (automation_id or "").strip()
    lim = max(1, min(int(limit), 200))
    q = (
        f"/{_RUN_TABLE}?automation_id=eq.{aid}&user_id=eq.{uid}&org_id=eq.{oid}"
        f"&order=started_at.desc&limit={lim}"
        "&select=id,automation_id,status,trigger_summary,result_summary,error,started_at,finished_at,duration_ms"
    )
    r = _client().get(_rest_url(q), headers=_headers())
    r.raise_for_status()
    rows = r.json()
    if not isinstance(rows, list):
        return []
    out: list[dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        out.append(
            {
                "id": raw["id"],
                "automation_id": raw["automation_id"],
                "status": raw["status"],
                "trigger_summary": raw.get("trigger_summary") or "",
                "result_summary": raw.get("result_summary"),
                "error": raw.get("error"),
                "started_at": raw.get("started_at"),
                "finished_at": raw.get("finished_at"),
                "duration_ms": raw.get("duration_ms"),
            }
        )
    return out
