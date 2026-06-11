"""Composio integrations API (connections UI)."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from koraku.core.auth import auth_error_detail, verify_request_auth
from koraku.core.config import settings
from koraku.core.product_hooks import product_hooks_active
from koraku.integrations import composio as composio_runtime
from koraku.workspace.paths import workspace_dir

router = APIRouter(prefix="/api/composio", tags=["composio"])


class ComposioConnectBody(BaseModel):
    toolkit: str = Field(..., min_length=2, max_length=64)


async def _composio_request_scope(
    authorization: str | None = Header(None),
) -> AsyncGenerator[None, None]:
    """
    Require auth when Composio is on, Cloud product hooks are active, or chat auth is required.
    Local SDK demo (auth off, no product hooks) may browse the static catalog without a session.
    """
    composio_runtime.configure_workspace_cache(workspace_dir())
    must_auth = (
        composio_runtime.is_configured()
        or product_hooks_active()
        or settings.require_auth_for_chat
    )
    if not must_auth:
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
    composio_runtime.cleanup_duplicate_toolkit_connections()
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


@router.get("/toolkits", dependencies=[Depends(_composio_request_scope)])
async def composio_toolkits_catalog(q: str = ""):
    """Curated integration catalog (~40 popular tools), resolved against Composio when configured."""
    if not composio_runtime.is_configured():
        return {
            "items": composio_runtime.list_curated_toolkits_static(query=q),
            "configured": False,
        }
    items = await asyncio.to_thread(lambda: composio_runtime.list_curated_toolkits(query=q))
    return {"items": items, "configured": True}


@router.get("/trigger-types", dependencies=[Depends(_composio_request_scope)])
async def composio_trigger_types():
    """Composio trigger slugs available for the signed-in user (connected toolkits only)."""
    if not composio_runtime.is_configured():
        return {"items": [], "configured": False}
    from koraku_cloud.automations.composio_triggers import list_trigger_options_for_user

    uid = composio_runtime.user_id()
    items = await asyncio.to_thread(list_trigger_options_for_user, uid)
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
