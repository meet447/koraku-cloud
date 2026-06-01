"""Memory UI: graph data from Supermemory (+ explicit personalization fallback)."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Query, Request

from koraku.core.auth import auth_error_detail
from koraku.core.request_auth import resolve_request_auth
from koraku.integrations.brain_graph import fetch_memory_graph_sync
from koraku.integrations.supermemory_client import supermemory_configured
from koraku.integrations.supabase_personalization import (
    fetch_personalization_sync,
    supabase_personalization_configured,
)

router = APIRouter(prefix="/api/memory", tags=["memory"])


def _auth_401(reason: str) -> HTTPException:
    return HTTPException(status_code=401, detail=auth_error_detail(reason))


@router.get("/graph")
async def memory_graph(
    request: Request,
    page: int = Query(1, ge=1, le=500),
    limit: int = Query(100, ge=1, le=200),
):
    """Memory graph nodes for the signed-in user."""
    resolved = resolve_request_auth(request)
    if not resolved.auth_ok:
        raise _auth_401(resolved.auth.reason)
    resolved.require_chat_access()
    if not resolved.sub:
        raise _auth_401("invalid_token")

    explicit_memory = ""
    explicit_soul = ""
    if supabase_personalization_configured():
        row = await asyncio.to_thread(fetch_personalization_sync, resolved.sub)
        if row:
            explicit_memory = row.get("memory") or ""
            explicit_soul = row.get("soul") or ""

    payload = await asyncio.to_thread(
        fetch_memory_graph_sync,
        resolved.sub,
        org_id=resolved.org_id,
        page=page,
        limit=limit,
        explicit_memory=explicit_memory,
        explicit_soul=explicit_soul,
    )
    payload["personalizationConfigured"] = supabase_personalization_configured()
    if not supermemory_configured() and not payload.get("documents"):
        payload["source"] = payload.get("source") or "empty"
        payload["supermemoryConfigured"] = False
    return payload
