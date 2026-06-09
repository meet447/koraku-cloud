"""Platform admin API — org search, credits, suspend (operators only)."""
from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from koraku_cloud.api.admin_auth import is_platform_admin_user_id_async, require_platform_admin
from koraku_cloud.integrations.supabase_admin import (
    fetch_audit_log_sync,
    fetch_dashboard_stats_sync,
    fetch_org_detail_sync,
    fetch_org_ledger_sync,
    grant_org_credits_sync,
    search_orgs_sync,
    update_org_admin_state_sync,
    update_org_period_sync,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


class GrantCreditsBody(BaseModel):
    grant_credits: int = Field(gt=0, le=10_000_000)
    reason: str = Field(default="", max_length=500)


class UpdatePeriodBody(BaseModel):
    credits_limit: int | None = Field(default=None, gt=0, le=100_000_000)
    plan: str | None = Field(default=None, max_length=16)


class UpdateAdminStateBody(BaseModel):
    suspended: bool | None = None
    suspend_reason: str = Field(default="", max_length=500)
    notes: str = Field(default="", max_length=2000)


@router.get("/me")
async def admin_me(request: Request):
    """Whether the current session is a platform admin."""
    from koraku.core.request_auth import resolve_request_auth

    resolved = resolve_request_auth(request)
    if not resolved.auth_ok or not resolved.sub:
        return {"admin": False}
    admin = await is_platform_admin_user_id_async(resolved.sub)
    return {"admin": admin, "user_id": resolved.sub}


@router.get("/dashboard")
async def admin_dashboard(request: Request):
    require_platform_admin(request)
    stats = await asyncio.to_thread(fetch_dashboard_stats_sync)
    audit = await asyncio.to_thread(fetch_audit_log_sync, limit=30)
    return {"stats": stats or {}, "audit": audit}


@router.get("/orgs/search")
async def admin_orgs_search(
    request: Request,
    q: str = Query("", min_length=0, max_length=120),
    limit: int = Query(25, ge=1, le=50),
):
    require_platform_admin(request)
    items = await asyncio.to_thread(search_orgs_sync, q, limit=limit)
    return {"items": items}


@router.get("/orgs/{org_id}")
async def admin_org_detail(request: Request, org_id: str):
    require_platform_admin(request)
    detail = await asyncio.to_thread(fetch_org_detail_sync, org_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Organization not found.")
    return detail


@router.get("/orgs/{org_id}/ledger")
async def admin_org_ledger(
    request: Request,
    org_id: str,
    limit: int = Query(50, ge=1, le=200),
):
    require_platform_admin(request)
    items = await asyncio.to_thread(fetch_org_ledger_sync, org_id, limit=limit)
    return {"items": items}


@router.post("/orgs/{org_id}/credits/grant")
async def admin_grant_credits(request: Request, org_id: str, body: GrantCreditsBody):
    resolved = require_platform_admin(request)
    actor = resolved.sub or ""
    key = f"adjust:admin:{actor}:{uuid.uuid4()}"
    try:
        result = await asyncio.to_thread(
            grant_org_credits_sync,
            org_id,
            grant_credits=body.grant_credits,
            reason=body.reason,
            actor_user_id=actor,
            idempotency_key=key,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    if result is None:
        raise HTTPException(status_code=502, detail="Could not grant credits.")
    return {"ok": True, **result}


@router.patch("/orgs/{org_id}/credits/period")
async def admin_update_period(request: Request, org_id: str, body: UpdatePeriodBody):
    resolved = require_platform_admin(request)
    actor = resolved.sub or ""
    try:
        row = await asyncio.to_thread(
            update_org_period_sync,
            org_id,
            credits_limit=body.credits_limit,
            plan=body.plan,
            actor_user_id=actor,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    if row is None:
        raise HTTPException(status_code=502, detail="Could not update period.")
    return {"ok": True, "period": row}


@router.patch("/orgs/{org_id}/state")
async def admin_update_state(request: Request, org_id: str, body: UpdateAdminStateBody):
    resolved = require_platform_admin(request)
    actor = resolved.sub or ""
    try:
        state = await asyncio.to_thread(
            update_org_admin_state_sync,
            org_id,
            suspended=body.suspended,
            suspend_reason=body.suspend_reason if body.suspended is not None else None,
            notes=body.notes if body.notes else None,
            actor_user_id=actor,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    if state is None:
        raise HTTPException(status_code=502, detail="Could not update org state.")
    return {"ok": True, "state": state}
