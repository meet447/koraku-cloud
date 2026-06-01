"""Composio integrations API (connections UI)."""
from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from koraku.core.auth import auth_error_detail, verify_request_auth
from koraku.integrations import composio as composio_runtime
from koraku.workspace.paths import workspace_dir

router = APIRouter(prefix="/api/composio", tags=["composio"])


class ComposioConnectBody(BaseModel):
    toolkit: str = Field(..., min_length=2, max_length=64)


async def _composio_request_scope(
    authorization: str | None = Header(None),
) -> AsyncGenerator[None, None]:
    """
    When Composio is configured, require a valid Supabase access token and scope all SDK calls
    to that user's ``sub``. When Composio is off, skip auth so the UI can show browse-only state.
    """
    composio_runtime.configure_workspace_cache(workspace_dir())
    if not composio_runtime.is_configured():
        yield
        return
    jwt_res = verify_request_auth(authorization)
    if not jwt_res.ok or not jwt_res.sub:
        status = 503 if jwt_res.reason == "no_secret" else 401
        detail = auth_error_detail(jwt_res.reason)
        raise HTTPException(status_code=status, detail=f"{detail} (code={jwt_res.reason})")
    uid = jwt_res.sub
    t = composio_runtime.set_composio_request_user(uid)
    try:
        yield
    finally:
        composio_runtime.reset_composio_request_user(t)


def _composio_overview_payload() -> dict:
    return {
        "configured": True,
        "user_id": composio_runtime.user_id(),
        "connections": composio_runtime.list_connections_summary(),
        "active_toolkits": composio_runtime.active_toolkit_slugs(),
    }


@router.get("/overview", dependencies=[Depends(_composio_request_scope)])
async def composio_overview():
    """Connection status + active toolkits for the Connections UI."""
    if not composio_runtime.is_configured():
        return {
            "configured": False,
            "user_id": None,
            "connections": [],
            "active_toolkits": [],
        }
    return await asyncio.to_thread(_composio_overview_payload)


_search_cache: dict[tuple[str, int], tuple[float, list[dict]]] = {}
_SEARCH_CACHE_TTL = 300.0
_SEARCH_CACHE_MAX_SIZE = 1000


@router.get("/toolkits", dependencies=[Depends(_composio_request_scope)])
async def composio_toolkits_search(q: str = "", limit: int = 48):
    if not composio_runtime.is_configured():
        return {"items": [], "configured": False}
    lim = max(1, min(int(limit), 50))

    now = time.monotonic()
    cache_key = (q, lim)
    if cache_key in _search_cache:
        cache_time, cached_items = _search_cache[cache_key]
        if (now - cache_time) < _SEARCH_CACHE_TTL:
            return {"items": cached_items, "configured": True}

    items = await asyncio.to_thread(lambda: composio_runtime.search_toolkits(q, limit=lim))

    if len(_search_cache) >= _SEARCH_CACHE_MAX_SIZE:
        _search_cache.clear()

    _search_cache[cache_key] = (now, items)
    return {"items": items, "configured": True}


@router.post("/connect", dependencies=[Depends(_composio_request_scope)])
async def composio_connect(body: ComposioConnectBody):
    if not composio_runtime.is_configured():
        raise HTTPException(status_code=503, detail="Set COMPOSIO_API_KEY to connect integrations.")
    try:
        return await asyncio.to_thread(composio_runtime.start_toolkit_auth, body.toolkit.strip().upper())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
