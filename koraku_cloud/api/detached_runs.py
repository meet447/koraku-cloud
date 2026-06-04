"""Background agent runs with SSE subscribe + replay (disconnect does not cancel the run).

With ``DETACHED_RUN_STORE_BACKEND=redis`` (or ``auto`` when ``REDIS_URL`` is set), chunks are
stored in Redis so ``GET /runs/{id}/stream`` can attach on any API worker. Otherwise buffers
are in-process only (same worker as ``POST /runs``).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import TYPE_CHECKING, Any, AsyncIterator, cast

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from koraku.api.chat_routes import StreamChatBody, _stream_agent_sse, format_sse
from koraku.core.config import settings
from koraku.credits.service import pre_check_org
from koraku.core.detached_run_store import (
    detached_gc_seconds,
    get_detached_run_store,
)
from koraku.core.rate_limit import RateLimit, enforce_rate_limit, rate_limit_key
from koraku.core.request_auth import resolve_request_auth
from koraku.core.tenant import reset_tenant_org_id, set_tenant_org_id
from koraku.integrations import composio as composio_runtime
from koraku.core.redact import redact_secrets
from koraku.integrations.cloud_user import reset_cloud_user_id, set_cloud_user_id

if TYPE_CHECKING:
    from koraku.agent import Agent

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

_DETACHED_GC_SEC = detached_gc_seconds()


def _resolve_run_id(raw_turn_id: str) -> str:
    """Use client ``turn_id`` as detached ``run_id`` when provided (production resume key)."""
    tid = (raw_turn_id or "").strip()
    if not tid:
        return str(uuid.uuid4())
    try:
        return str(uuid.UUID(tid))
    except ValueError as e:
        raise HTTPException(status_code=400, detail="turn_id must be a valid UUID") from e


async def _schedule_gc(run_id: str, owner_org_id: str | None) -> None:
    await asyncio.sleep(_DETACHED_GC_SEC)
    await get_detached_run_store().drop(run_id, owner_org_id=owner_org_id)


async def _run_worker(
    run_id: str,
    body: StreamChatBody,
    auth_sub: str | None,
    auth_org_id: str | None,
    agent: Agent | None,
    server_mode: str,
) -> None:
    store = get_detached_run_store()
    buf = await store.get(run_id, owner_org_id=auth_org_id)
    if buf is None:
        return

    composio_token: Token | None = None
    cloud_token: Token | None = None
    tenant_token: Token | None = None
    try:
        tenant_token = set_tenant_org_id(auth_org_id)
        if auth_sub:
            composio_token = composio_runtime.set_composio_request_user(auth_sub)
            cloud_token = set_cloud_user_id(auth_sub)
        async for chunk in _stream_agent_sse(
            body.msg.strip(),
            images=body.images,
            model=body.model,
            provider=body.provider,
            session_id=(body.session_id.strip() or None),
            client_tz=body.client_tz,
            client_locale=body.client_locale,
            agent=cast(Any, agent),
            server_mode=server_mode,
            auth_sub=auth_sub,
            auth_org_id=auth_org_id,
            stream_run_id=run_id,
        ):
            await buf.append(chunk)
    except Exception as e:
        logger.exception(
            "detached run worker failed: %s",
            redact_secrets(str(e)),
        )
        await buf.append(format_sse({"type": "agent.error", "data": {"error": redact_secrets(str(e))}}))
        await buf.append("event: done\n\n")
    finally:
        composio_runtime.reset_composio_request_user(composio_token)
        reset_cloud_user_id(cloud_token)
        reset_tenant_org_id(tenant_token)
        await buf.finish()
        asyncio.create_task(
            _schedule_gc(run_id, auth_org_id),
            name=f"gc-detached-run-{run_id}",
        )


@router.post("/runs")
async def start_detached_run(body: StreamChatBody, request: Request) -> JSONResponse:
    """Start an agent run in the background; subscribe with ``GET /runs/{run_id}/stream``."""
    resolved = resolve_request_auth(request)
    resolved.require_chat_access()
    auth_sub = resolved.sub
    auth_org_id = resolved.org_id
    enforce_rate_limit(
        RateLimit(
            key=rate_limit_key(
                request, scope="detached-runs", user_id=auth_sub, org_id=auth_org_id
            ),
            limit=settings.chat_rate_limit_per_minute,
        )
    )
    await pre_check_org(auth_org_id)

    agent = getattr(request.app.state, "koraku_agent", None)
    server_mode = getattr(request.app.state, "server_mode", "unconfigured")
    run_id = _resolve_run_id(body.turn_id)
    store = get_detached_run_store()
    existing = await store.get(run_id, owner_org_id=auth_org_id)
    if existing is not None:
        if not existing.allows(auth_sub, auth_org_id):
            if existing.owner_sub and auth_sub is None:
                raise HTTPException(status_code=401, detail="Authorization required for this run.")
            raise HTTPException(status_code=403, detail="This run belongs to another user")
        return JSONResponse({"run_id": run_id})

    await store.register(run_id, owner_sub=auth_sub, owner_org_id=auth_org_id)

    asyncio.create_task(
        _run_worker(run_id, body, auth_sub, auth_org_id, agent, server_mode),
        name=f"koraku-detached-{run_id}",
    )
    return JSONResponse({"run_id": run_id})


@router.get("/runs/{run_id}/status")
async def detached_run_status(run_id: str, request: Request) -> JSONResponse:
    """JSON run state for mobile / reconnect (``not_found`` after GC or unknown run)."""
    resolved = resolve_request_auth(request)
    auth_sub = resolved.sub
    auth_org_id = resolved.org_id

    buf = await get_detached_run_store().get(run_id, owner_org_id=auth_org_id)
    if buf is None:
        return JSONResponse(
            {
                "run_id": run_id,
                "state": "not_found",
                "last_event_id": -1,
                "buffered_chunks": 0,
                "hint": "Run finished, expired, or is on a different API instance. Send again if needed.",
            },
            status_code=200,
        )

    if not buf.allows(auth_sub, auth_org_id):
        if buf.owner_sub and auth_sub is None:
            raise HTTPException(status_code=401, detail="Authorization required for this run.")
        raise HTTPException(status_code=403, detail="This run belongs to another user")

    snap = await buf.status_snapshot()
    if snap.get("state") == "not_found":
        return JSONResponse(
            {
                "run_id": run_id,
                "state": "not_found",
                "last_event_id": -1,
                "buffered_chunks": 0,
                "hint": "Run finished, expired, or is on a different API instance. Send again if needed.",
            },
            status_code=200,
        )

    return JSONResponse({"run_id": run_id, **snap})


@router.get("/runs/{run_id}/stream")
async def stream_detached_run(
    run_id: str,
    request: Request,
    after: int = Query(-1, ge=-1, description="Replay chunks with SSE id greater than this value."),
) -> StreamingResponse:
    """SSE replay + live tail for a detached run (browser may disconnect; run continues)."""
    resolved = resolve_request_auth(request)
    auth_sub = resolved.sub
    auth_org_id = resolved.org_id

    buf = await get_detached_run_store().get(run_id, owner_org_id=auth_org_id)
    if buf is None:
        raise HTTPException(status_code=404, detail="Unknown or expired run_id")

    if not buf.allows(auth_sub, auth_org_id):
        if buf.owner_sub and auth_sub is None:
            raise HTTPException(
                status_code=401,
                detail="Authorization required to subscribe to this run.",
            )
        raise HTTPException(status_code=403, detail="This run belongs to another user")

    hdr_after = request.headers.get("last-event-id") or request.headers.get("Last-Event-ID")
    if hdr_after is not None and str(hdr_after).strip().isdigit():
        after = max(after, int(str(hdr_after).strip()))

    async def gen() -> AsyncIterator[str]:
        try:
            async for chunk in buf.subscribe(after):
                yield chunk
        except asyncio.CancelledError:
            raise
        except TimeoutError as e:
            logger.warning(
                "detached run stream interrupted by Redis timeout run_id=%s: %s",
                run_id,
                redact_secrets(str(e)),
            )
        except Exception as e:
            logger.exception(
                "detached run stream failed run_id=%s: %s",
                run_id,
                redact_secrets(str(e)),
            )
            yield format_sse(
                {"type": "agent.error", "data": {"error": "Stream interrupted. Reconnect or check run status."}}
            )
            yield "event: done\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
