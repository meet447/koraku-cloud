"""Background agent runs with SSE subscribe + replay (disconnect does not cancel the run).

Buffers are in-process only: subscribe must hit the same worker that accepted ``POST /runs``.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from contextvars import Token
from typing import TYPE_CHECKING, Any, AsyncIterator, cast

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from koraku.api.chat_routes import StreamChatBody, _stream_agent_sse, format_sse
from koraku.core.config import settings
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

# After a run finishes, drop its in-memory buffer (override in tests via monkeypatch).
_DETACHED_GC_SEC = float((os.environ.get("KORAKU_DETACHED_RUN_GC_SECONDS") or "600").strip() or "600")

# Max buffered SSE chunks per run (memory cap; older runs should finish or be GC'd).
_MAX_CHUNKS_PER_RUN = 12_000
_SUBSCRIBER_QUEUE_MAX = max(16, int(settings.detached_run_subscriber_queue_max))

_SENTINEL: object = object()


class _RunBuffer:
    __slots__ = (
        "owner_sub",
        "owner_org_id",
        "chunks",
        "next_seq",
        "done",
        "lock",
        "subscribers",
    )

    def __init__(self, owner_sub: str | None, owner_org_id: str | None = None) -> None:
        self.owner_sub = owner_sub
        self.owner_org_id = owner_org_id
        self.chunks: list[tuple[int, str]] = []
        self.next_seq = 0
        self.done = False
        self.lock = asyncio.Lock()
        self.subscribers: list[asyncio.Queue[Any]] = []

    def allows(self, auth_sub: str | None, auth_org_id: str | None = None) -> bool:
        if self.owner_sub is None:
            return True
        if auth_sub != self.owner_sub:
            return False
        if self.owner_org_id and auth_org_id != self.owner_org_id:
            return False
        return True

    async def append(self, raw_chunk: str) -> None:
        async with self.lock:
            if self.done:
                return
            seq = self.next_seq
            self.next_seq += 1
            if raw_chunk.startswith("id: "):
                wrapped = raw_chunk
            else:
                wrapped = f"id: {seq}\n{raw_chunk}"
            self.chunks.append((seq, wrapped))
            if len(self.chunks) > _MAX_CHUNKS_PER_RUN:
                self.chunks.pop(0)
            subs = list(self.subscribers)
        slow_subscribers: list[asyncio.Queue[Any]] = []
        for q in subs:
            try:
                q.put_nowait(wrapped)
            except asyncio.QueueFull:
                slow_subscribers.append(q)
                try:
                    q.put_nowait(_SENTINEL)
                except asyncio.QueueFull:
                    pass
        if slow_subscribers:
            async with self.lock:
                for q in slow_subscribers:
                    try:
                        self.subscribers.remove(q)
                    except ValueError:
                        pass

    async def finish(self) -> None:
        async with self.lock:
            self.done = True
            subs = list(self.subscribers)
            self.subscribers.clear()
        for q in subs:
            try:
                await q.put(_SENTINEL)
            except Exception:
                pass

    async def status_snapshot(self) -> dict[str, Any]:
        """Lightweight state for reconnect UX (same worker as the run)."""
        async with self.lock:
            done = self.done
            nchunks = len(self.chunks)
            last_id = self.chunks[-1][0] if self.chunks else -1
        return {
            "state": "completed" if done else "running",
            "last_event_id": last_id,
            "buffered_chunks": nchunks,
        }

    async def subscribe(self, after: int) -> AsyncIterator[str]:
        # Bounded so a slow live subscriber cannot grow memory without limit. Replay remains capped
        # by ``_MAX_CHUNKS_PER_RUN``; live subscribers that fall behind are disconnected.
        q: asyncio.Queue[Any] = asyncio.Queue(maxsize=_SUBSCRIBER_QUEUE_MAX)
        try:
            async with self.lock:
                is_done = self.done
                if not is_done:
                    self.subscribers.append(q)
                replay = [(s, w) for s, w in self.chunks if s > after]
            for _, w in replay:
                yield w
            if is_done:
                return
            while True:
                item = await q.get()
                if item is _SENTINEL:
                    break
                yield item
        finally:
            async with self.lock:
                try:
                    self.subscribers.remove(q)
                except ValueError:
                    pass


_registry: dict[str, _RunBuffer] = {}
_registry_lock = asyncio.Lock()


async def _schedule_gc(run_id: str) -> None:
    await asyncio.sleep(_DETACHED_GC_SEC)
    async with _registry_lock:
        _registry.pop(run_id, None)


async def _run_worker(
    run_id: str,
    body: StreamChatBody,
    auth_sub: str | None,
    auth_org_id: str | None,
    agent: Agent | None,
    server_mode: str,
) -> None:
    b = _registry.get(run_id)
    if b is None:
        return
    buf = b

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
        asyncio.create_task(_schedule_gc(run_id), name=f"gc-detached-run-{run_id}")


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

    agent = getattr(request.app.state, "koraku_agent", None)
    server_mode = getattr(request.app.state, "server_mode", "unconfigured")
    run_id = str(uuid.uuid4())
    buf = _RunBuffer(owner_sub=auth_sub, owner_org_id=auth_org_id)
    async with _registry_lock:
        _registry[run_id] = buf

    asyncio.create_task(
        _run_worker(run_id, body, auth_sub, auth_org_id, agent, server_mode),
        name=f"koraku-detached-{run_id}",
    )
    return JSONResponse({"run_id": run_id})


@router.get("/runs/{run_id}/status")
async def detached_run_status(run_id: str, request: Request) -> JSONResponse:
    """JSON run state for mobile / reconnect (in-process; ``not_found`` after GC or on another worker)."""
    resolved = resolve_request_auth(request)
    auth_sub = resolved.sub
    auth_org_id = resolved.org_id

    async with _registry_lock:
        buf = _registry.get(run_id)
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

    async with _registry_lock:
        buf = _registry.get(run_id)
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

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
