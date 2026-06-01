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
from koraku.automations.validation import validate_cron_expression, validate_timezone_iana
from koraku.core.auth import auth_error_detail, verify_request_auth
from koraku.core.config import settings
from koraku.core.rate_limit import RateLimit, enforce_rate_limit, rate_limit_key
from koraku.integrations.cloud_user import (
    effective_cloud_user_id,
    reset_cloud_user_id,
    set_cloud_user_id,
)

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


async def _automations_request_scope(
    authorization: str | None = Header(None),
) -> AsyncGenerator[None, None]:
    """Require Supabase JWT and backend Supabase REST credentials; bind tenant id via ``effective_cloud_user_id``."""
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
    t = set_cloud_user_id(uid)
    try:
        yield
    finally:
        reset_cloud_user_id(t)


def _user_id() -> str:
    return effective_cloud_user_id()


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
        else:
            if not (self.event_display or "").strip():
                raise ValueError(
                    "event automations require event_display (e.g. 'Gmail: New email')"
                )
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


@router.get("", dependencies=[Depends(_automations_request_scope)])
async def automations_list():
    uid = _user_id()
    rows = await async_ops.list_automations(uid)
    items = await enrich_automation_rows(list(rows))
    return {"items": items}


@router.post("", dependencies=[Depends(_automations_request_scope)])
async def automations_create(body: AutomationCreate, request: Request):
    uid = _user_id()
    enforce_rate_limit(
        RateLimit(
            key=rate_limit_key(request, scope="automation-create", user_id=uid),
            limit=settings.automation_rate_limit_per_minute,
        )
    )
    row = await async_ops.insert_automation(
        uid,
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


@router.get("/{automation_id}", dependencies=[Depends(_automations_request_scope)])
async def automations_get(automation_id: str):
    uid = _user_id()
    row = await async_ops.get_automation(uid, automation_id)
    if not row:
        raise HTTPException(status_code=404, detail="Automation not found")
    return await enrich_automation_row(row)


@router.patch("/{automation_id}", dependencies=[Depends(_automations_request_scope)])
async def automations_patch(automation_id: str, body: AutomationPatch):
    uid = _user_id()
    existing = await async_ops.get_automation(uid, automation_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Automation not found")
    patch = body.model_dump(exclude_unset=True)
    if not patch:
        return await enrich_automation_row(existing)
    row = await async_ops.update_automation(
        uid,
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


@router.delete("/{automation_id}", dependencies=[Depends(_automations_request_scope)])
async def automations_delete(automation_id: str):
    uid = _user_id()
    if not await async_ops.delete_automation(uid, automation_id):
        raise HTTPException(status_code=404, detail="Automation not found")
    await automation_scheduler.sync_scheduler_jobs_async()
    return {"ok": True}


@router.get("/{automation_id}/runs", dependencies=[Depends(_automations_request_scope)])
async def automations_runs(automation_id: str, limit: int = 50):
    uid = _user_id()
    if not await async_ops.get_automation(uid, automation_id):
        raise HTTPException(status_code=404, detail="Automation not found")
    return {"items": await async_ops.list_runs(uid, automation_id, limit=limit)}


@router.post("/{automation_id}/run", dependencies=[Depends(_automations_request_scope)])
async def automations_run_now(automation_id: str, request: Request):
    uid = _user_id()
    enforce_rate_limit(
        RateLimit(
            key=rate_limit_key(request, scope="automation-run", user_id=uid),
            limit=settings.automation_rate_limit_per_minute,
        )
    )
    if not await async_ops.get_automation(uid, automation_id):
        raise HTTPException(status_code=404, detail="Automation not found")
    if not await _try_acquire_manual_run_slot(uid):
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
            uid,
            automation_id,
            agent=agent,
            trigger_summary="Manual run from the Automations page.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Automation run crashed: {e!s}"
        ) from e
    finally:
        await _release_manual_run_slot(uid)
