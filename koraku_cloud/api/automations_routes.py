"""FastAPI routes for saved automations (CRUD, runs, manual run)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator

from koraku_cloud.automations import (
    async_ops,
    runner as automation_runner,
    scheduler as automation_scheduler,
)
from koraku_cloud.automations.present import enrich_automation_row, enrich_automation_rows
from koraku_cloud.automations.supabase_store import supabase_automations_configured
from koraku_cloud.automations.schedule import preset_to_cron
from koraku_cloud.automations.validation import (
    validate_cron_expression,
    validate_timezone_iana,
)
from koraku_cloud.automations.webhook_tokens import (
    generate_webhook_token,
    hash_webhook_token,
)
from dataclasses import dataclass
from typing import Any

from koraku.core.auth import auth_error_detail, verify_request_auth
from koraku.core.config import settings as app_settings
from koraku.core.rate_limit import RateLimit, enforce_rate_limit, rate_limit_key
from koraku.core.tenant import reset_tenant_org_id, set_tenant_org_id
from koraku.integrations.cloud_user import reset_cloud_user_id, set_cloud_user_id
from koraku_cloud.integrations.supabase_tenant import parse_org_header, resolve_org_id_sync

router = APIRouter(prefix="/api/automations", tags=["automations"])

_manual_run_inflight: dict[str, int] = {}
_manual_run_inflight_lock = asyncio.Lock()


async def _try_acquire_manual_run_slot(uid: str) -> bool:
    limit = max(1, app_settings.automation_manual_run_concurrency_per_user)
    async with _manual_run_inflight_lock:
        if _manual_run_inflight.get(uid, 0) >= limit:
            return False
        _manual_run_inflight[uid] = _manual_run_inflight.get(uid, 0) + 1
        return True


async def _release_manual_run_slot(uid: str) -> None:
    async with _manual_run_inflight_lock:
        n = _manual_run_inflight.get(uid, 0) - 1
        if n <= 0:
            _manual_run_inflight.pop(uid, None)
        else:
            _manual_run_inflight[uid] = n


@dataclass(frozen=True)
class AutomationsAuth:
    user_id: str
    org_id: str


async def _automations_request_scope(
    request: Request,
    authorization: str | None = Header(None),
) -> AsyncGenerator[AutomationsAuth, None]:
    """Require Supabase JWT, org membership, and bind user/org context for row scope."""
    if not supabase_automations_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Automations require SUPABASE_URL (or NEXT_PUBLIC_SUPABASE_URL) and "
                "SUPABASE_SERVICE_ROLE_KEY on the Koraku backend."
            ),
        )
    jwt_res = verify_request_auth(authorization)
    if not jwt_res.ok or not jwt_res.sub:
        status = 503 if jwt_res.reason == "no_secret" else 401
        detail = auth_error_detail(jwt_res.reason)
        raise HTTPException(
            status_code=status, detail=f"{detail} (code={jwt_res.reason})"
        )
    uid = jwt_res.sub
    requested = parse_org_header(request.headers)
    org_id, reason = resolve_org_id_sync(uid, requested)
    if not org_id:
        if reason == "org_forbidden":
            raise HTTPException(status_code=403, detail="You do not have access to this organization.")
        raise HTTPException(
            status_code=503,
            detail="Tenant service unavailable. Check Supabase configuration.",
        )
    cloud_tok = set_cloud_user_id(uid)
    tenant_tok = set_tenant_org_id(org_id)
    try:
        yield AutomationsAuth(user_id=uid, org_id=org_id)
    finally:
        reset_tenant_org_id(tenant_tok)
        reset_cloud_user_id(cloud_tok)


class SchedulePresetBody(BaseModel):
    kind: str = Field(
        ...,
        pattern="^(every_n_minutes|daily|weekdays|weekly|custom)$",
    )
    every_n_minutes: int | None = Field(default=None, ge=1, le=59)
    hour: int | None = Field(default=None, ge=0, le=23)
    minute: int | None = Field(default=None, ge=0, le=59)
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    cron_expression: str | None = None


class SchedulePreviewBody(BaseModel):
    timezone: str = Field(..., min_length=1)
    schedule_preset: SchedulePresetBody


class AutomationCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    headline: str = Field(default="", max_length=200)
    natural_language_spec: str = Field(..., min_length=1, max_length=50_000)
    trigger_mode: str = Field(..., pattern="^(scheduled|event)$")
    status: str = Field(default="active", pattern="^(active|paused)$")
    timezone: str | None = None
    cron_expression: str | None = None
    schedule_preset: SchedulePresetBody | None = None
    event_display: str | None = Field(default=None, max_length=200)
    toolkits: list[str] = Field(default_factory=list, max_length=24)

    @model_validator(mode="after")
    def check_trigger_fields(self) -> "AutomationCreate":
        if self.trigger_mode == "scheduled":
            tz = (self.timezone or "").strip()
            if not tz:
                raise ValueError("scheduled automations require timezone")
            validate_timezone_iana(tz)
            if self.schedule_preset is None and not (self.cron_expression or "").strip():
                raise ValueError(
                    "scheduled automations require schedule_preset or cron_expression"
                )
        return self


def _resolve_schedule(
    *,
    trigger_mode: str,
    timezone: str | None,
    cron_expression: str | None,
    schedule_preset: SchedulePresetBody | None,
) -> tuple[str | None, str | None, dict[str, Any] | None]:
    if trigger_mode == "event":
        return None, None, None
    tz = (timezone or "").strip()
    preset_dict: dict[str, Any] | None = None
    cron = (cron_expression or "").strip() or None
    if schedule_preset is not None:
        preset_dict = schedule_preset.model_dump(exclude_none=True)
        cron = preset_to_cron(preset_dict)
    elif cron:
        validate_cron_expression(cron)
        preset_dict = {"kind": "custom", "cron_expression": cron}
    if not cron or not tz:
        raise ValueError("scheduled automations require timezone and a valid schedule")
    return tz, cron, preset_dict


def _webhook_public_url(request: Request, automation_id: str, token: str) -> str:
    base = (getattr(app_settings, "koraku_public_api_url", None) or "").strip().rstrip("/")
    if not base:
        proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "https").strip()
        host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or "").strip()
        if host:
            base = f"{proto}://{host}".rstrip("/")
        else:
            base = str(request.base_url).rstrip("/")
    return f"{base}/api/automation-events/{automation_id}?token={token}"


class AutomationPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    headline: str | None = Field(default=None, max_length=200)
    natural_language_spec: str | None = Field(
        default=None, min_length=1, max_length=50_000
    )
    status: str | None = Field(default=None, pattern="^(active|paused)$")
    timezone: str | None = None
    cron_expression: str | None = None
    event_display: str | None = Field(default=None, max_length=200)
    toolkits: list[str] | None = Field(default=None, max_length=24)
    schedule_preset: SchedulePresetBody | None = None
    reset_failure_count: bool | None = None

    @model_validator(mode="after")
    def check_cron(self) -> "AutomationPatch":
        if self.cron_expression is not None:
            validate_cron_expression(self.cron_expression)
        if self.timezone is not None:
            validate_timezone_iana(self.timezone)
        return self


@router.get("")
async def automations_list(auth: AutomationsAuth = Depends(_automations_request_scope)):
    rows = await async_ops.list_automations(auth.user_id, auth.org_id)
    items = await enrich_automation_rows(list(rows))
    return {"items": items}


@router.post("/schedule/preview")
async def automations_schedule_preview(
    body: SchedulePreviewBody,
    auth: AutomationsAuth = Depends(_automations_request_scope),
):
    _ = auth
    tz = validate_timezone_iana(body.timezone.strip())
    preset = body.schedule_preset.model_dump(exclude_none=True)
    cron = preset_to_cron(preset)
    nxt = await async_ops.compute_next_cron_fire(cron, tz)
    return {
        "cron_expression": cron,
        "timezone": tz,
        "next_run_at": nxt.isoformat() if nxt else None,
    }


@router.post("")
async def automations_create(
    body: AutomationCreate,
    request: Request,
    auth: AutomationsAuth = Depends(_automations_request_scope),
):
    enforce_rate_limit(
        RateLimit(
            key=rate_limit_key(
                request, scope="automation-create", user_id=auth.user_id, org_id=auth.org_id
            ),
            limit=app_settings.automation_rate_limit_per_minute,
        )
    )
    try:
        tz, cron, preset_dict = _resolve_schedule(
            trigger_mode=body.trigger_mode,
            timezone=body.timezone,
            cron_expression=body.cron_expression,
            schedule_preset=body.schedule_preset,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    webhook_hash: str | None = None
    plain_token: str | None = None
    if body.trigger_mode == "event":
        plain_token = generate_webhook_token()
        webhook_hash = hash_webhook_token(plain_token)
    row = await async_ops.insert_automation(
        auth.user_id,
        auth.org_id,
        title=body.title,
        headline=body.headline,
        natural_language_spec=body.natural_language_spec,
        trigger_mode=body.trigger_mode,  # type: ignore[arg-type]
        status=body.status,  # type: ignore[arg-type]
        timezone=tz,
        cron_expression=cron,
        event_display=body.event_display or (
            "Webhook" if body.trigger_mode == "event" else None
        ),
        toolkits=body.toolkits,
        schedule_preset=preset_dict,
        event_webhook_token_hash=webhook_hash,
    )
    await automation_scheduler.sync_scheduler_jobs_async()
    out = await enrich_automation_row(row)
    if plain_token:
        out["webhook_token"] = plain_token
        out["webhook_url"] = _webhook_public_url(request, row["id"], plain_token)
    return out


@router.get("/{automation_id}")
async def automations_get(
    automation_id: str, auth: AutomationsAuth = Depends(_automations_request_scope)
):
    row = await async_ops.get_automation(auth.user_id, automation_id, org_id=auth.org_id)
    if not row:
        raise HTTPException(status_code=404, detail="Automation not found")
    return await enrich_automation_row(row)


@router.patch("/{automation_id}")
async def automations_patch(
    automation_id: str,
    body: AutomationPatch,
    auth: AutomationsAuth = Depends(_automations_request_scope),
):
    existing = await async_ops.get_automation(
        auth.user_id, automation_id, org_id=auth.org_id
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Automation not found")
    patch = body.model_dump(exclude_unset=True)
    if not patch:
        return await enrich_automation_row(existing)
    tz = patch.get("timezone")
    cron = patch.get("cron_expression")
    preset_dict = None
    if body.schedule_preset is not None:
        try:
            tz, cron, preset_dict = _resolve_schedule(
                trigger_mode=str(existing.get("trigger_mode") or "scheduled"),
                timezone=tz or existing.get("timezone"),
                cron_expression=cron,
                schedule_preset=body.schedule_preset,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
    consecutive = 0 if patch.pop("reset_failure_count", None) else None
    row = await async_ops.update_automation(
        auth.user_id,
        auth.org_id,
        automation_id,
        title=patch.get("title"),
        headline=patch.get("headline"),
        natural_language_spec=patch.get("natural_language_spec"),
        status=patch.get("status"),  # type: ignore[arg-type]
        timezone=tz if tz is not None or preset_dict else patch.get("timezone"),
        cron_expression=cron if cron is not None or preset_dict else patch.get("cron_expression"),
        event_display=patch.get("event_display"),
        toolkits=patch.get("toolkits"),
        schedule_preset=preset_dict,
        consecutive_failures=consecutive,
    )
    await automation_scheduler.sync_scheduler_jobs_async()
    assert row is not None
    return await enrich_automation_row(row)


@router.delete("/{automation_id}")
async def automations_delete(
    automation_id: str, auth: AutomationsAuth = Depends(_automations_request_scope)
):
    if not await async_ops.delete_automation(auth.user_id, auth.org_id, automation_id):
        raise HTTPException(status_code=404, detail="Automation not found")
    await automation_scheduler.sync_scheduler_jobs_async()
    return {"ok": True}


@router.get("/{automation_id}/runs")
async def automations_runs(
    automation_id: str,
    limit: int = 50,
    auth: AutomationsAuth = Depends(_automations_request_scope),
):
    if not await async_ops.get_automation(auth.user_id, automation_id, org_id=auth.org_id):
        raise HTTPException(status_code=404, detail="Automation not found")
    return {
        "items": await async_ops.list_runs(
            auth.user_id, auth.org_id, automation_id, limit=limit
        )
    }


@router.get("/{automation_id}/runs/{run_id}")
async def automations_get_run(
    automation_id: str,
    run_id: str,
    auth: AutomationsAuth = Depends(_automations_request_scope),
):
    if not await async_ops.get_automation(auth.user_id, automation_id, org_id=auth.org_id):
        raise HTTPException(status_code=404, detail="Automation not found")
    row = await async_ops.get_run(auth.user_id, auth.org_id, run_id)
    if not row or row.get("automation_id") != automation_id:
        raise HTTPException(status_code=404, detail="Run not found")
    return row


@router.post("/{automation_id}/run")
async def automations_run_now(
    automation_id: str,
    request: Request,
    auth: AutomationsAuth = Depends(_automations_request_scope),
):
    enforce_rate_limit(
        RateLimit(
            key=rate_limit_key(
                request, scope="automation-run", user_id=auth.user_id, org_id=auth.org_id
            ),
            limit=app_settings.automation_rate_limit_per_minute,
        )
    )
    if not await async_ops.get_automation(auth.user_id, automation_id, org_id=auth.org_id):
        raise HTTPException(status_code=404, detail="Automation not found")
    if not await _try_acquire_manual_run_slot(auth.user_id):
        raise HTTPException(
            status_code=429,
            detail=(
                "Another automation run is already in flight for your account. "
                "Wait for it to finish, then try again."
            ),
        )
    agent = getattr(request.app.state, "koraku_agent", None)
    try:
        result = await automation_runner.queue_automation_run(
            auth.user_id,
            automation_id,
            org_id=auth.org_id,
            agent=agent,
            trigger_summary="Manual run from the Automations page.",
        )
        status_code = 202 if result.get("status") == "running" else 200
        return JSONResponse(status_code=status_code, content=result)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Automation run crashed: {e!s}"
        ) from e
    finally:
        await _release_manual_run_slot(auth.user_id)
