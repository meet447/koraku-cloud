"""Execute a saved automation via the Koraku agent (scheduled, manual, or future event runs)."""
from __future__ import annotations

import asyncio
import logging
import time
from contextvars import Token
from typing import TYPE_CHECKING, Any, Callable

from koraku.integrations.blaxel_lazy import clear_lazy_blaxel_session, set_lazy_blaxel_session
from koraku.agent.runtime_context import AgentRunContext
from koraku.automations import async_ops
from koraku.automations.run_context import prepare_automation_agent_context, reset_automation_tenant
from koraku.core.config import settings
from koraku.core.models import SessionState, utcnow
from koraku.integrations import composio as composio_runtime
from koraku.integrations.cloud_user import reset_cloud_user_id, set_cloud_user_id
from koraku.integrations.supermemory_client import (
    extract_last_assistant_text,
    ingest_chat_turn_sync,
    supermemory_configured,
)
from koraku.workspace.paths import workspace_dir

if TYPE_CHECKING:
    from koraku.agent.run import Agent

log = logging.getLogger(__name__)

# Avoid overlapping runs for the same automation (scheduler + manual).
_run_guard: dict[str, asyncio.Lock] = {}


def _lock_for(automation_id: str) -> asyncio.Lock:
    lock = _run_guard.get(automation_id)
    if lock is None:
        lock = asyncio.Lock()
        _run_guard[automation_id] = lock
    return lock


def _blocks_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            t = block.get("text")
            if isinstance(t, str) and t.strip():
                parts.append(t.strip())
    return "\n\n".join(parts).strip()


def _last_assistant_summary(session: SessionState, max_chars: int = 2000) -> str:
    for msg in reversed(session.messages):
        if getattr(msg, "role", None) == "assistant":
            text = _blocks_to_text(msg.content)
            if text:
                return text[:max_chars]
    return ""


def _normalize_toolkits(raw: Any) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(x).strip().upper() for x in raw if str(x).strip()]
    return []


async def _run_agent_session_with_timeout(
    agent: Agent,
    user_msg: str,
    session: SessionState,
    _emit: Callable[[dict[str, Any]], None],
    agent_workspace: str,
    auto: dict[str, Any],
    *,
    account_personalization: dict[str, str] | None = None,
    user_id: str = "",
    org_id: str | None = None,
    run_id: str = "",
) -> str | None:
    last_error: str | None = None

    async def _consume_agent() -> None:
        nonlocal last_error
        async for ev in agent.run(
            user_msg,
            session,
            _emit,
            workspace=agent_workspace,
            client_timezone=auto.get("timezone"),
            client_locale=None,
            image_parts=None,
            max_steps_override=settings.automation_max_steps,
            run_context=AgentRunContext(),
            cloud_sandbox=None,
            account_personalization=account_personalization,
            run_id=run_id or None,
        ):
            if ev.get("type") == "agent.error":
                d = ev.get("data") or {}
                last_error = str(d.get("error") or ev)

    try:
        await asyncio.wait_for(
            _consume_agent(),
            timeout=float(settings.automation_run_timeout_seconds),
        )
    except asyncio.TimeoutError:
        last_error = (
            f"Automation run exceeded {float(settings.automation_run_timeout_seconds):.0f}s time limit."
        )
    except Exception as e:
        last_error = str(e)
    finally:
        if user_id and supermemory_configured():
            assistant_text = extract_last_assistant_text(session)
            if user_msg.strip() or assistant_text:
                await asyncio.to_thread(
                    ingest_chat_turn_sync,
                    user_id,
                    user_text=user_msg.strip(),
                    assistant_text=assistant_text,
                    org_id=org_id,
                    session_id=session.session_id,
                    run_id=run_id or None,
                )

    return last_error


async def _finalize_automation_run(
    user_id: str,
    automation_id: str,
    run_id: str,
    status: str,
    err: str | None,
    res: str | None,
    started: Any,
    finished: Any,
) -> None:
    await async_ops.finish_run(
        user_id,
        run_id,
        status=status,  # type: ignore[arg-type]
        result_summary=res,
        error=err,
        started_at=started,
        finished_at=finished,
    )
    await async_ops.set_automation_run_times(user_id, automation_id, last_run_at=finished)

    try:
        from koraku.automations import scheduler

        await asyncio.to_thread(scheduler.refresh_next_run_metadata, user_id, automation_id)
    except Exception:
        log.exception(
            "refresh_next_run_metadata failed user=%s automation=%s", user_id, automation_id
        )


async def _handle_missing_agent(
    user_id: str, automation_id: str, run_id: str, started: Any
) -> dict[str, Any]:
    await async_ops.finish_run(
        user_id,
        run_id,
        status="failed",
        result_summary=None,
        error="LLM is not configured on this server.",
        started_at=started,
        finished_at=utcnow(),
    )
    await async_ops.set_automation_run_times(user_id, automation_id, last_run_at=utcnow())
    return {"ok": False, "error": "llm_not_configured", "run_id": run_id}


def build_automation_user_message(
    *,
    title: str,
    natural_language_spec: str,
    trigger_summary: str,
    toolkits: list[str] | None = None,
) -> str:
    tk = _normalize_toolkits(toolkits or [])
    toolkit_line = ""
    if tk:
        toolkit_line = (
            f"\n**Preferred integrations:** When you need external apps, call **ComposioRun** "
            f"with these ACTIVE toolkit slugs where relevant: {', '.join(tk)}.\n"
        )
    return (
        "You are executing a saved Koraku automation (automated run).\n\n"
        f"**Automation title:** {title}\n\n"
        f"**What the user wants:**\n{natural_language_spec.strip()}\n\n"
        f"**Trigger context:**\n{trigger_summary.strip()}\n"
        f"{toolkit_line}\n"
        "Follow the instructions completely. Prefer concrete actions (tools) when needed. "
        "End with a short summary of what you did."
    )


async def execute_automation(
    user_id: str,
    automation_id: str,
    *,
    agent: Agent | None,
    trigger_summary: str,
    emit: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Run one automation turn; persists a row in ``koraku_automation_run`` (Supabase)."""
    lock = _lock_for(automation_id)

    async with lock:
        cloud_tok: Token | None = None
        comp_tok: Token | None = None
        tenant_tok: Any | None = None
        try:
            cloud_tok = set_cloud_user_id(user_id)
            comp_tok = composio_runtime.set_composio_request_user(user_id)
            composio_runtime.configure_workspace_cache(workspace_dir())

            auto = await async_ops.get_automation(user_id, automation_id)
            if auto is None:
                return {"ok": False, "error": "automation_not_found"}

            started = utcnow()
            run_id = await async_ops.insert_run_start(
                user_id, automation_id, trigger_summary=trigger_summary
            )

            if agent is None:
                return await _handle_missing_agent(user_id, automation_id, run_id, started)

            session = SessionState(session_id=f"auto-{automation_id}-{run_id}")
            user_msg = build_automation_user_message(
                title=auto["title"],
                natural_language_spec=auto["natural_language_spec"],
                trigger_summary=trigger_summary,
                toolkits=auto.get("toolkits"),
            )

            org_id, account_p, tenant_tok = await prepare_automation_agent_context(
                user_id,
                spec_query=auto.get("natural_language_spec"),
            )

            lazy_tok = set_lazy_blaxel_session(session.session_id)

            def _emit(ev: dict[str, Any]) -> None:
                if emit is not None:
                    emit(ev)

            t0 = time.perf_counter()
            try:
                last_error = await _run_agent_session_with_timeout(
                    agent,
                    user_msg,
                    session,
                    _emit,
                    workspace_dir(),
                    auto,
                    account_personalization=account_p,
                    user_id=user_id,
                    org_id=org_id,
                    run_id=run_id,
                )
            finally:
                clear_lazy_blaxel_session(lazy_tok)

            finished = utcnow()
            summary = _last_assistant_summary(session)
            if summary and not last_error:
                status = "success"
                err = None
                res = summary
            else:
                status = "failed"
                err = last_error or "No assistant output captured."
                res = summary or None

            await _finalize_automation_run(
                user_id, automation_id, run_id, status, err, res, started, finished
            )

            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            log.info(
                "automation_run automation_id=%s run_id=%s status=%s duration_ms=%s",
                automation_id,
                run_id,
                status,
                elapsed_ms,
            )
            return {
                "ok": status == "success",
                "run_id": run_id,
                "status": status,
                "duration_ms": elapsed_ms,
                "error": err,
                "result_summary": res,
            }
        finally:
            reset_automation_tenant(tenant_tok)
            composio_runtime.reset_composio_request_user(comp_tok)
            reset_cloud_user_id(cloud_tok)
