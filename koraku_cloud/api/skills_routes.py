"""Org-scoped agent skills API (Supabase)."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from koraku.core.auth import auth_error_detail
from koraku.core.request_auth import resolve_request_auth
from koraku_cloud.integrations.supabase_skills import (
    delete_org_skill_sync,
    fetch_org_skills_sync,
    supabase_skills_configured,
    upsert_org_skill_sync,
)

router = APIRouter(prefix="/api", tags=["skills"])


class SkillUpsertBody(BaseModel):
    name: str = Field(default="", max_length=120)
    description: str = Field(default="", max_length=1024)
    body: str = Field(default="", max_length=120_000)
    enabled: bool = True


def _auth_401(reason: str) -> HTTPException:
    return HTTPException(status_code=401, detail=auth_error_detail(reason))


def _require_database() -> None:
    if not supabase_skills_configured():
        raise HTTPException(
            status_code=503,
            detail="Skills require Supabase (SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY).",
        )


@router.get("/skills")
async def skills_list(request: Request):
    """List enabled skills for the active organization."""
    _require_database()
    resolved = resolve_request_auth(request)
    if not resolved.auth_ok:
        raise _auth_401(resolved.auth.reason)
    resolved.require_chat_access()
    if not resolved.sub:
        raise _auth_401("invalid_token")
    rows = await asyncio.to_thread(
        fetch_org_skills_sync,
        resolved.sub,
        org_id=resolved.org_id,
        enabled_only=False,
    )
    if rows is None:
        raise HTTPException(status_code=502, detail="Could not load skills from database.")
    return {"items": rows}


@router.put("/skills/{slug}")
async def skills_upsert(request: Request, slug: str, body: SkillUpsertBody):
    """Create or update a skill for the active organization."""
    _require_database()
    resolved = resolve_request_auth(request)
    if not resolved.auth_ok:
        raise _auth_401(resolved.auth.reason)
    resolved.require_chat_access()
    if not resolved.sub:
        raise _auth_401("invalid_token")
    try:
        await asyncio.to_thread(
            upsert_org_skill_sync,
            resolved.sub,
            org_id=resolved.org_id,
            slug=slug,
            name=body.name,
            description=body.description,
            body=body.body,
            enabled=body.enabled,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not save skill: {e}") from e
    return {"ok": True}


@router.delete("/skills/{slug}")
async def skills_delete(request: Request, slug: str):
    """Remove a skill from the active organization."""
    _require_database()
    resolved = resolve_request_auth(request)
    if not resolved.auth_ok:
        raise _auth_401(resolved.auth.reason)
    resolved.require_chat_access()
    if not resolved.sub:
        raise _auth_401("invalid_token")
    try:
        await asyncio.to_thread(
            delete_org_skill_sync,
            resolved.sub,
            org_id=resolved.org_id,
            slug=slug,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not delete skill: {e}") from e
    return {"ok": True}
