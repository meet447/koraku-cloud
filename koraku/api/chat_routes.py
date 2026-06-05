"""Chat UI API: model list + SSE ``/stream``."""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import uuid
from contextvars import Token
from typing import TYPE_CHECKING, Any, AsyncIterator, Literal

log = logging.getLogger(__name__)

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator, model_validator

from koraku.agent import _step_budget, get_or_create_chat_session
from koraku.core.session_store import get_session_store
from koraku.agent.runtime_context import AgentRunContext, ExecutionTarget
from koraku.agent.unconfigured import run_unconfigured
from koraku.core.config import settings
from koraku.credits.service import (
    credits_summary_event,
    pre_check_org,
    settle_run,
)
from koraku.core.rate_limit import RateLimit, enforce_rate_limit, rate_limit_key
from koraku.core.request_auth import resolve_request_auth
from koraku.core.tenant import reset_tenant_org_id, set_tenant_org_id
from koraku.core.redact import redact_secrets
from koraku.integrations import composio as composio_runtime
from koraku.integrations.blaxel_lazy import (
    clear_lazy_blaxel_session,
    set_lazy_blaxel_session,
    warm_blaxel_session_background,
)
from koraku.integrations.blaxel_runtime import (
    cloud_blaxel_block_reason,
    session_workspace_root_posix,
    user_sandbox_is_cached,
)
from koraku.integrations.cloud_user import (
    effective_cloud_user_id,
    reset_cloud_user_id,
    set_cloud_user_id,
)
from koraku.api.chat_hydration import (
    after_turn_memory_ingest,
    fetch_account_personalization,
    hydrate_session_for_turn,
)
from koraku.core.product_hooks import product_hooks_active
from koraku.llm.catalog import resolve_provider_and_model, ui_chat_models
from koraku.streaming import KorakuStreamState, map_koraku_stream_events
from koraku.tools.registry import tools_for_execution_target
from koraku.workspace.paths import workspace_dir

if TYPE_CHECKING:
    from koraku.agent import Agent

router = APIRouter(tags=["chat"])


def normalize_stream_execution_target(value: str | None) -> ExecutionTarget:
    from koraku.core.config import is_cloud_configured

    if is_cloud_configured():
        return "cloud"
    raw = (value or settings.default_execution_target or "local").strip().lower()
    if raw in ("local", "server", "cloud"):
        return raw  # type: ignore[return-value]
    return "local"


class StreamImagePart(BaseModel):
    """One inline image as raw base64 (no ``data:`` URL prefix)."""

    media_type: str = Field(..., max_length=64)
    data: str = Field(..., max_length=14_000_000)

    @field_validator("media_type")
    @classmethod
    def must_be_image_mime(cls, v: str) -> str:
        m = v.strip().lower()
        allowed = {"image/jpeg", "image/png", "image/gif", "image/webp"}
        if m not in allowed:
            raise ValueError("media_type must be image/jpeg, image/png, image/gif, or image/webp")
        return m


class StreamClientHistoryMessage(BaseModel):
    """One visible prior chat message sent by the browser as a hydration fallback."""

    role: Literal["user", "assistant"]
    text: str = Field(..., max_length=20_000)


def client_history_rows_for_hydration(
    rows: list[StreamClientHistoryMessage] | list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Normalize client history for hydration (Pydantic models or plain dicts)."""
    out: list[dict[str, Any]] = []
    for row in rows or []:
        if isinstance(row, dict):
            out.append(row)
        elif isinstance(row, BaseModel):
            out.append(row.model_dump())
        else:
            out.append({"role": getattr(row, "role", "user"), "text": getattr(row, "text", "")})
    return out


class StreamChatBody(BaseModel):
    """JSON body for ``POST /stream`` (SSE response)."""

    msg: str = Field(default="", max_length=400_000)
    model: str = ""
    provider: str = ""
    session_id: str = ""
    client_tz: str | None = None
    client_locale: str | None = None
    images: list[StreamImagePart] = Field(default_factory=list, max_length=8)
    client_history: list[StreamClientHistoryMessage] = Field(default_factory=list, max_length=40)
    # Client turn UUID; when set on ``POST /runs`` it becomes the detached ``run_id`` (idempotent resume).
    turn_id: str = Field(default="", max_length=64)
    # ``local`` | ``server`` | ``cloud`` — defaults to ``DEFAULT_EXECUTION_TARGET`` / profile.
    execution_target: str = Field(default="", max_length=16)

    @model_validator(mode="after")
    def msg_or_images(self) -> "StreamChatBody":
        if not (self.msg.strip() or self.images):
            raise ValueError("Provide a non-empty message and/or at least one image")
        tid = (self.turn_id or "").strip()
        if tid:
            try:
                uuid.UUID(tid)
            except ValueError as e:
                raise ValueError("turn_id must be a valid UUID") from e
        return self


def format_sse(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data)}\n\n"


def _normalize_client_hint(value: str | None) -> str | None:
    s = (value or "").strip()
    return s or None


async def _yield_error_events(error_msg: str, stream_state: KorakuStreamState) -> AsyncIterator[str]:
    for row in map_koraku_stream_events({"type": "agent.error", "data": {"error": error_msg}}, stream_state):
        yield format_sse(row)
        await asyncio.sleep(0)


async def _yield_sse_events_from_queue(
    queue: asyncio.Queue[dict | None],
    task: asyncio.Task,
    stream_state: KorakuStreamState,
) -> AsyncIterator[str]:
    idle = max(5.0, float(settings.sse_keepalive_seconds))
    ping = f"event: ping\ndata: {json.dumps({})}\n\n"
    while True:
        try:
            event = await asyncio.wait_for(queue.get(), timeout=idle)
        except asyncio.TimeoutError:
            if task.done():
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    break
            else:
                yield ping
                continue
        if event is None:
            break
        for row in map_koraku_stream_events(event, stream_state):
            yield format_sse(row)
            await asyncio.sleep(0)


async def _stream_agent_sse(
    msg: str,
    *,
    images: list[StreamImagePart],
    model: str,
    provider: str,
    session_id: str | None,
    client_tz: str | None,
    client_locale: str | None,
    agent: "Agent | None",
    server_mode: str,
    auth_sub: str | None = None,
    auth_org_id: str | None = None,
    client_history: list[StreamClientHistoryMessage] | list[dict[str, Any]] | None = None,
    request: Request | None = None,
    cancel_event: asyncio.Event | None = None,
    stream_run_id: str | None = None,
    execution_target: ExecutionTarget | None = None,
) -> AsyncIterator[str]:
    session = await asyncio.to_thread(
        get_or_create_chat_session,
        session_id, owner_sub=auth_sub, owner_org_id=auth_org_id
    )
    eff_provider, resolved_model = resolve_provider_and_model(provider, model)
    budget = msg.strip() or ("[images]" if images else "")
    exec_target = execution_target or normalize_stream_execution_target(None)
    blaxel_lazy = exec_target == "cloud" and cloud_blaxel_block_reason(settings) is None

    stream_state = KorakuStreamState()
    if stream_run_id and str(stream_run_id).strip():
        stream_state.run_id = str(stream_run_id).strip()
    if images:
        stream_state.usage.image_count = len(images)
    stream_state.resolved_model = resolved_model if server_mode == "live" else "koraku-unconfigured"
    stream_state.eff_provider = eff_provider if server_mode == "live" else "unconfigured"

    eff_cancel: asyncio.Event | None = cancel_event
    watch_disconnect: asyncio.Task[None] | None = None
    if request is not None:
        eff_cancel = cancel_event or asyncio.Event()

        async def _disconnect_watcher() -> None:
            try:
                while True:
                    if await request.is_disconnected():
                        eff_cancel.set()
                        return
                    await asyncio.sleep(0.3)
            except asyncio.CancelledError:
                return

        watch_disconnect = asyncio.create_task(_disconnect_watcher())

    async def _stop_disconnect_watch() -> None:
        if watch_disconnect is not None:
            watch_disconnect.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await watch_disconnect

    # Flush preamble immediately so the UI shows activity while we load history / sandbox.
    yield format_sse(
        stream_state.started_payload(stream_state.resolved_model, chat_session_id=session.session_id)
    )
    await asyncio.sleep(0)
    yield format_sse(stream_state.s2_stream_payload())
    await asyncio.sleep(0)
    yield format_sse(stream_state.route_decision_payload())
    await asyncio.sleep(0)

    personalization_task: asyncio.Task | None = None
    if auth_sub:
        personalization_task = asyncio.create_task(
            fetch_account_personalization(auth_sub, auth_org_id)
        )
    hydration_task = asyncio.create_task(
        hydrate_session_for_turn(
            session,
            incoming_user_text=msg.strip(),
            auth_sub=auth_sub,
            auth_org_id=auth_org_id,
            client_history=client_history_rows_for_hydration(client_history),
        )
    )

    pending: list[asyncio.Task] = [hydration_task]
    if personalization_task is not None:
        pending.append(personalization_task)
    core_results = await asyncio.gather(*pending, return_exceptions=True)

    idx = 0
    hydration = core_results[idx]
    idx += 1
    if isinstance(hydration, BaseException):
        log.warning("chat history hydration failed: %s", hydration)
        from koraku.core.chat_history import ChatHistoryHydration

        hydration = ChatHistoryHydration(
            session_id=session.session_id,
            source="memory",
            reason="hydration_error",
            auth_present=bool(auth_sub),
            supabase_configured=True,
            rows_fetched=0,
            messages_loaded=len(session.messages),
            messages_before=len(session.messages),
        )

    account_p: dict[str, str] | None = None
    if personalization_task is not None:
        fetched = core_results[idx]
        if not isinstance(fetched, BaseException):
            account_p = fetched if fetched is not None else {"agent_name": "", "memory": "", "soul": ""}
        else:
            log.warning("personalization fetch failed: %s", fetched)

    mode_hint, max_steps_hint = _step_budget(budget)
    tz = _normalize_client_hint(client_tz)
    loc = _normalize_client_hint(client_locale)
    blaxel_on = blaxel_lazy
    koraku_boot = {
        "workspace_session_id": session.session_id,
        "runId": stream_state.run_id,
        "server_mode": server_mode,
        "mode": mode_hint,
        "max_steps": max_steps_hint,
        "execution_target": exec_target,
        "blaxel_sandbox": blaxel_on,
        "blaxel_lazy": blaxel_lazy,
        "blaxel_cached": (
            user_sandbox_is_cached(effective_cloud_user_id())
            if blaxel_lazy and product_hooks_active() and auth_sub
            else False
        ),
        "tool_names": [
            t.name for t in tools_for_execution_target(exec_target, blaxel_sandbox_active=blaxel_on)
        ],
        "provider": stream_state.eff_provider,
        "model": stream_state.resolved_model,
        "client_timezone": tz,
        "client_locale": loc,
    }
    init_cwd = workspace_dir()
    if blaxel_lazy and product_hooks_active() and auth_sub:
        init_cwd = session_workspace_root_posix(
            effective_cloud_user_id(),
            session.session_id,
            settings,
        )
    yield format_sse(stream_state.system_init_payload(init_cwd, koraku_boot))
    await asyncio.sleep(0)
    for row in map_koraku_stream_events({"type": "agent.history", "data": hydration.to_trace_data()}, stream_state):
        yield format_sse(row)
        await asyncio.sleep(0)

    queue_max = max(16, int(settings.detached_run_subscriber_queue_max))
    queue: asyncio.Queue[dict | None] = asyncio.Queue(maxsize=queue_max)

    def emit(event: dict) -> None:
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            # Slow consumer: signal cancel so the agent unwinds rather than buffering forever.
            if eff_cancel is not None and not eff_cancel.is_set():
                log.warning("chat SSE producer queue full; cancelling run %s", stream_state.run_id)
                eff_cancel.set()

    async def run_agent() -> None:
        lazy_tok, lazy_root_tok = (
            set_lazy_blaxel_session(session.session_id) if blaxel_lazy else (None, None)
        )
        warm_task: asyncio.Task[None] | None = None
        if blaxel_lazy and product_hooks_active() and auth_sub and user_sandbox_is_cached(
            effective_cloud_user_id()
        ):
            warm_task = asyncio.create_task(warm_blaxel_session_background())
        try:
            img_payload = [{"media_type": p.media_type, "data": p.data} for p in images]
            agent_iter = (
                run_unconfigured(msg, session, emit, image_parts=img_payload)
                if agent is None
                else agent.run(
                    msg,
                    session,
                    emit,
                    model=model,
                    provider=provider,
                    client_timezone=tz,
                    client_locale=loc,
                    image_parts=img_payload,
                    run_context=AgentRunContext(execution_target=exec_target),
                    cloud_sandbox=None,
                    account_personalization=account_p,
                    run_id=stream_state.run_id,
                    cancel_event=eff_cancel,
                )
            )
            async for _ in agent_iter:
                pass
        except Exception as e:
            emit({"type": "agent.error", "data": {"error": redact_secrets(str(e))}})
        finally:
            if warm_task is not None and not warm_task.done():
                warm_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await warm_task
            await after_turn_memory_ingest(
                auth_sub=auth_sub,
                auth_org_id=auth_org_id,
                msg=msg,
                session=session,
                run_id=stream_state.run_id,
            )
            session.touch()
            await asyncio.to_thread(get_session_store().save, session)
            clear_lazy_blaxel_session(lazy_tok, lazy_root_tok)
            try:
                queue.put_nowait(None)
            except asyncio.QueueFull:
                # Sentinel couldn't fit: consumer's idle timeout will end the stream.
                pass

    task = asyncio.create_task(run_agent())

    async for chunk in _yield_sse_events_from_queue(queue, task, stream_state):
        yield chunk

    if not task.done():
        # Disconnect path: if the agent is blocked in an external call, signal
        # cancel and force-cancel after a short grace so the request handler
        # cannot await it indefinitely.
        if eff_cancel is not None and not eff_cancel.is_set():
            eff_cancel.set()
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=5.0)
        except asyncio.TimeoutError:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task
        except Exception:
            log.exception("agent task ended with error after disconnect")
    else:
        with contextlib.suppress(Exception):
            await task

    await _stop_disconnect_watch()

    if auth_org_id and server_mode == "live":
        credits_payload = await settle_run(
            auth_org_id,
            run_id=stream_state.run_id,
            usage=stream_state.usage,
            kind="chat",
            model=stream_state.resolved_model,
            provider=stream_state.eff_provider,
        )
        credit_evt = credits_summary_event(credits_payload)
        if credit_evt:
            yield format_sse(credit_evt)
            await asyncio.sleep(0)

    yield "event: done\n\n"


@router.get("/api/chat-models")
async def chat_models(request: Request):
    """Model IDs for the chat UI dropdown (per provider + optional CHAT_MODEL_OPTIONS)."""
    resolved = resolve_request_auth(request)
    resolved.require_chat_access()
    return ui_chat_models()


@router.post("/stream")
async def stream_endpoint_post(body: StreamChatBody, request: Request):
    """SSE streaming agent chat. Use JSON body (large prompts); response is ``text/event-stream``."""
    resolved = resolve_request_auth(request)
    resolved.require_chat_access()
    auth_sub = resolved.sub
    auth_org_id = resolved.org_id
    await enforce_rate_limit(
        RateLimit(
            key=rate_limit_key(
                request, scope="chat-stream", user_id=auth_sub, org_id=auth_org_id
            ),
            limit=settings.chat_rate_limit_per_minute,
        )
    )
    await pre_check_org(auth_org_id)

    agent = getattr(request.app.state, "koraku_agent", None)
    server_mode = getattr(request.app.state, "server_mode", "unconfigured")

    async def event_generator() -> AsyncIterator[str]:
        composio_token: Token | None = None
        cloud_token: Token | None = None
        tenant_token: Token | None = None
        try:
            tenant_token = set_tenant_org_id(auth_org_id)
            if auth_sub:
                composio_token = composio_runtime.set_composio_request_user(auth_sub)
                cloud_token = set_cloud_user_id(auth_sub)
            exec_target = normalize_stream_execution_target(body.execution_target or None)
            async for chunk in _stream_agent_sse(
                body.msg.strip(),
                images=body.images,
                model=body.model,
                provider=body.provider,
                session_id=(body.session_id.strip() or None),
                client_tz=body.client_tz,
                client_locale=body.client_locale,
                agent=agent,
                server_mode=server_mode,
                auth_sub=auth_sub,
                auth_org_id=auth_org_id,
                client_history=list(body.client_history),
                request=request,
                execution_target=exec_target,
            ):
                yield chunk
        finally:
            composio_runtime.reset_composio_request_user(composio_token)
            reset_cloud_user_id(cloud_token)
            reset_tenant_org_id(tenant_token)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
