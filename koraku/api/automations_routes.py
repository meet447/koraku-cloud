"""FastAPI routes for saved automations (CRUD, runs, manual run)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

from koraku.automations import (
    async_ops,
    runner as automation_runner,
    scheduler as automation_scheduler,
)
from koraku.automations.present import enrich_automation_row, enrich_automation_rows
from koraku.automations.supabase_store import supabase_automations_configured
from koraku.automations.validation import (
    EVENT_TRIGGER_UNAVAILABLE,
    validate_cron_expression,
    validate_timezone_iana,
)
from dataclasses import dataclass

from koraku.core.auth import auth_error_detail, verify_request_auth
from koraku.core.config import settings
from koraku.core.rate_limit import RateLimit, enforce_rate_limit, rate_limit_key
from koraku.core.tenant import reset_tenant_org_id, set_tenant_org_id
from koraku.integrations.cloud_user import reset_cloud_user_id, set_cloud_user_id
from koraku.integrations.supabase_tenant import parse_org_header, resolve_org_id_sync

router = APIRouter(prefix="/api/automations", tags=["automations"])

_manual_run_inflight: dict[str, int] = {}
_manual_run_inflight_lock = asyncio.Lock()


async def _try_acquire_manual_run_slot(uid: str) -> bool:
    limit = max(1, settings.automation_manual_run_concurrency_per_user)
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


class AutomationCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    headline: str = Field(default="", max_length=200)
    natural_language_spec: str = Field(..., min_length=1, max_length=50_000)
    trigger_mode: str = Field(..., pattern="^(scheduled|event)$")
    status: str = Field(default="active", pattern="^(active|paused)$")
    timezone: str | None = None
    cron_expression: str | None = None
    event_display: str | None = Field(default=None, max_length=200)
    toolkits: list[str] = Field(default_factory=list, max_length=24)

    @model_validator(mode="after")
    def check_trigger_fields(self) -> "AutomationCreate":
        if self.trigger_mode == "event":
            raise ValueError(EVENT_TRIGGER_UNAVAILABLE)
        if self.trigger_mode == "scheduled":
            if (
                not (self.timezone or "").strip()
                or not (self.cron_expression or "").strip()
            ):
                raise ValueError(
                    "scheduled automations require timezone and cron_expression"
                )
            validate_timezone_iana(self.timezone or "")
            validate_cron_expression(self.cron_expression or "")
        return self


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
            limit=settings.automation_rate_limit_per_minute,
        )
    )
    row = await async_ops.insert_automation(
        auth.user_id,
        auth.org_id,
        title=body.title,
        headline=body.headline,
        natural_language_spec=body.natural_language_spec,
        trigger_mode=body.trigger_mode,  # type: ignore[arg-type]
        status=body.status,  # type: ignore[arg-type]
        timezone=body.timezone,
        cron_expression=body.cron_expression,
        event_display=body.event_display,
        toolkits=body.toolkits,
    )
    await automation_scheduler.sync_scheduler_jobs_async()
    return await enrich_automation_row(row)


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
    row = await async_ops.update_automation(
        auth.user_id,
        auth.org_id,
        automation_id,
        title=patch.get("title"),
        headline=patch.get("headline"),
        natural_language_spec=patch.get("natural_language_spec"),
        status=patch.get("status"),  # type: ignore[arg-type]
        timezone=patch.get("timezone"),
        cron_expression=patch.get("cron_expression"),
        event_display=patch.get("event_display"),
        toolkits=patch.get("toolkits"),
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
            limit=settings.automation_rate_limit_per_minute,
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
        return await automation_runner.execute_automation(
            auth.user_id,
            automation_id,
            org_id=auth.org_id,
            agent=agent,
            trigger_summary="Manual run from the Automations page.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Automation run crashed: {e!s}"
        ) from e
    finally:
        await _release_manual_run_slot(auth.user_id)
