"""Personalization: per-user profile in Supabase."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from koraku.core.auth import auth_error_detail
from koraku.core.request_auth import resolve_request_auth
from koraku.integrations.supabase_personalization import (
    fetch_personalization_sync,
    supabase_personalization_configured,
    upsert_personalization_sync,
)

router = APIRouter(prefix="/api", tags=["personalization"])


class PersonalizationUpdate(BaseModel):
    """Agent display name plus long-form memory and soul text."""

    agent_name: str = Field(default="", max_length=120)
    memory: str = Field(default="", max_length=600_000)
    soul: str = Field(default="", max_length=600_000)


def _auth_401(reason: str) -> HTTPException:
    return HTTPException(status_code=401, detail=auth_error_detail(reason))


def _require_database() -> None:
    if not supabase_personalization_configured():
        raise HTTPException(
            status_code=503,
            detail="Personalization requires Supabase (SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY).",
        )


@router.get("/personalization")
async def personalization_get(request: Request):
    """Load profile from Supabase for the signed-in user."""
    _require_database()
    resolved = resolve_request_auth(request)
    if not resolved.auth_ok:
        raise _auth_401(resolved.auth.reason)
    resolved.require_chat_access()
    row = await asyncio.to_thread(
        fetch_personalization_sync, resolved.sub or "", org_id=resolved.org_id
    )
    if row is None:
        raise HTTPException(status_code=502, detail="Could not load personalization from database.")
    return row


@router.put("/personalization")
async def personalization_put(request: Request, body: PersonalizationUpdate):
    """Persist profile to Supabase for the signed-in user."""
    _require_database()
    resolved = resolve_request_auth(request)
    if not resolved.auth_ok:
        raise _auth_401(resolved.auth.reason)
    resolved.require_chat_access()
    if not resolved.sub:
        raise _auth_401("invalid_token")
    try:
        await asyncio.to_thread(
            upsert_personalization_sync,
            resolved.sub,
            body.agent_name,
            body.memory,
            body.soul,
            org_id=resolved.org_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not save personalization: {e}") from e
    return {"ok": True}
