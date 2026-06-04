"""Koraku agent — one ReAct loop for every turn (Claude Code–style), with workspace skills + memory."""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
import time
from typing import Any, AsyncIterator, Callable

from koraku.core.config import settings
from koraku.core.redact import redact_secrets
from koraku.core.models import AgentMessage, SessionState
from koraku.agent.context_manager import ContextManager
from koraku.llm.client import UnifiedLLMClient
from koraku.llm.catalog import resolve_effective_model, resolve_provider_id
from koraku.tools.runtime import set_active_session
from koraku.tools.policy import tool_stdout_indicates_error
from koraku.agent.runtime_context import (
    AgentRunContext,
    bind_execution_target,
    reset_execution_target,
    resolve_agent_workspace,
    resolve_execution_target,
)
from koraku.tools.registry import tools_for_execution_target
from koraku.tools.tool_def import Tool
from koraku.integrations import composio as composio_runtime
from koraku.agent.composio_delegate_context import (
    ComposioDelegateContext,
    reset_composio_delegate_context,
    set_composio_delegate_context,
)
from koraku.tools.composio_delegate_tool import COMPOSIO_RUN_TOOL
from koraku.agent.blaxel_scope import blaxel_sandbox_scope, blaxel_session_workspace_scope
from koraku.integrations.blaxel_runtime import resolve_blaxel_session_root
from koraku.integrations.cloud_user import effective_cloud_user_id
from koraku.workspace.agent_workspace import agent_workspace_scope
from koraku.agent.prompt_builder import build_tiered_system_prompt, prefetch_learned_memory_volatile
from koraku.agent.prompt_sections import format_runtime_context_section
from koraku.agent.budget import (
    BUDGET_EXHAUSTED_USER,
    BUDGET_STEERING_USER,
    LOOP_STEERING_USER,
    LoopTracker,
    TurnLimits,
    composio_max_rounds_for_goal,
    composio_wall_seconds_for_goal,
    composio_worker_sop_appendix,
    classify_composio_goal,
    resolve_turn_limits,
    tools_for_composio_worker,
    dispatcher_mode_active,
    dispatcher_system_appendix,
    tools_for_dispatcher_turn,
)


log = logging.getLogger(__name__)

_AGENT_RUN_SEMAPHORE = asyncio.Semaphore(max(1, int(settings.agent_concurrency_limit)))
_TOOL_RUN_SEMAPHORE = asyncio.Semaphore(max(1, int(settings.tool_concurrency_limit)))
_WORKING_MEMORY_MAX_ITEMS = 8
_WORKING_MEMORY_ITEM_CHARS = 360
_WORKING_MEMORY_TOTAL_CHARS = 2_000


def _emit_worker_status(
    emit: Callable[[dict[str, Any]], None],
    message: str,
    *,
    tool_name: str | None = None,
    phase: str | None = None,
) -> None:
    data: dict[str, Any] = {"trace": "worker_status", "message": message}
    if tool_name:
        data["tool"] = tool_name
    if phase:
        data["phase"] = phase
    emit({"type": "agent.trace", "data": data})


def _resolve_tool_from_active(tool_name: str, active_tools: list[Any]) -> Tool | None:
    resolved = "WebFetch" if tool_name == "WebPage" else tool_name
    for t in active_tools:
        if t.name == resolved:
            return t
    return None


def build_user_message_blocks(
    user_input: str,
    image_parts: list[dict[str, str]],
) -> str | list[dict[str, Any]]:
    """Plain string when no images; otherwise Anthropic-shaped user blocks (images then text)."""
    if not image_parts:
        return user_input
    blocks: list[dict[str, Any]] = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": p.get("media_type") or "image/png",
                "data": p.get("data") or "",
            },
        }
        for p in image_parts
    ]
    text = user_input.strip() or "The user attached image(s). Answer based on what you see."
    blocks.append({"type": "text", "text": text})
    return blocks


def _get_mode_and_budget(
    budget_text: str, max_steps_override: int | None
) -> tuple[str, int]:
    """Legacy helper: mode label + round safety cap (prefer :func:`resolve_turn_limits`)."""
    mode, limits = resolve_turn_limits(budget_text, max_steps_override)
    return mode, limits.max_rounds


def _step_budget(user_input: str) -> tuple[str, int]:
    """Used by chat API hints; mirrors :func:`resolve_turn_limits` round cap."""
    mode, limits = resolve_turn_limits(user_input, None)
    return mode, limits.max_rounds


def _snippet_text(text: str, max_chars: int, truncated_note: str) -> str:
    s = text or ""
    if len(s) > max_chars:
        return s[:max_chars] + truncated_note
    return s


def _clean_one_line(text: str, max_chars: int = _WORKING_MEMORY_ITEM_CHARS) -> str:
    s = re.sub(r"\s+", " ", text or "").strip()
    if len(s) > max_chars:
        return s[: max_chars - 3].rstrip() + "..."
    return s


def _tool_result_summary(tool_result: dict[str, Any]) -> dict[str, str] | None:
    content = tool_result.get("content", "")
    tool_id = str(tool_result.get("tool_use_id") or "").strip()
    prefix = f"{tool_id}: " if tool_id else ""

    if tool_result.get("is_error"):
        return {"type": "error", "summary": prefix + _clean_one_line(str(content), 220)}
    if not isinstance(content, str) or not content.strip():
        return None

    stripped = content.strip()
    if stripped.startswith("[") and "url" in stripped:
        try:
            rows = json.loads(stripped)
        except (TypeError, ValueError):
            rows = None
        if isinstance(rows, list):
            sources: list[str] = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                title = _clean_one_line(str(row.get("title") or row.get("name") or "Source"), 90)
                url = _clean_one_line(str(row.get("url") or ""), 140)
                if url:
                    sources.append(f"{title} ({url})")
                if len(sources) >= 3:
                    break
            if sources:
                return {"type": "sources", "summary": prefix + "Found sources: " + "; ".join(sources)}
        return {"type": "sources", "summary": prefix + f"Found {stripped.count('url')} source-like results."}

    if len(stripped) < 80:
        return None
    return {"type": "content", "summary": prefix + _clean_one_line(stripped)}


def format_working_memory_context(memory: list[dict[str, Any]]) -> AgentMessage | None:
    """Small per-run scratchpad shown to later loop steps, not durable memory."""
    if not memory:
        return None
    lines = [
        "## Working memory for this run",
        "Transient findings from tools. Use these to avoid re-reading, but do not treat them as durable user memory.",
    ]
    total = sum(len(line) + 1 for line in lines)
    for item in reversed(memory[-_WORKING_MEMORY_MAX_ITEMS:]):
        kind = _clean_one_line(str(item.get("type") or "note"), 40)
        summary = _clean_one_line(str(item.get("summary") or ""))
        line = f"- {kind}: {summary}"
        if total + len(line) + 1 > _WORKING_MEMORY_TOTAL_CHARS:
            lines.append("- note: Additional findings omitted to keep context small.")
            break
        lines.append(line)
        total += len(line) + 1
    return AgentMessage(role="user", content="\n".join(lines))


def build_composio_subagent_system_prompt(
    workspace: str,
    toolkits: list[str],
    client_timezone: str | None = None,
    client_locale: str | None = None,
    execution_environment_note: str | None = None,
    *,
    cloud_tool_root: str | None = None,
    goal_class: str = "integration_full",
) -> str:
    """Narrow system prompt for a Composio-only scoped run."""
    ws = os.path.abspath(workspace)
    runtime = format_runtime_context_section(client_timezone, client_locale)
    env_extra = f"\n{execution_environment_note}\n" if execution_environment_note else ""
    ctr = ""
    if cloud_tool_root:
        ctr = f"\n- File tools use paths relative to `{cloud_tool_root.rstrip('/')}`.\n"
    tk = ", ".join(toolkits)
    return f"""You are Koraku's **integration worker** (scoped background agent).

## Task
- Composio toolkits in this run: **{tk}**.
- Fulfill the latest **user** message using those Composio tools plus workspace and web tools as needed.
- Do **not** claim inbox/calendar counts, 'no emails', or 'nothing found' until after you have run the relevant list/fetch tool and read the response.
- Before any send, post, or external write: confirm recipients, timing, and content from tool results.

{runtime}

## Workspace
- Root: `{ws}`{ctr}{env_extra}

## Reply
- Finish with a concise summary the main Koraku agent can relay: outcomes, errors, ids, times, or links.
- Do not mention ComposioRun, sub-agents, or internal architecture.
{composio_worker_sop_appendix(goal_class)}
"""


def _subagent_final_assistant_text(session: SessionState) -> str:
    for msg in reversed(session.messages):
        if msg.role != "assistant":
            continue
        c = msg.content
        if isinstance(c, str):
            t = c.strip()
            if t:
                return t
        if isinstance(c, list):
            texts: list[str] = []
            for block in c:
                if isinstance(block, dict) and block.get("type") == "text":
                    texts.append(str(block.get("text") or ""))
            joined = "\n".join(texts).strip()
            if joined:
                return joined
    return "No assistant text was produced in the integration run."


def build_system_prompt(
    workspace: str,
    client_timezone: str | None = None,
    client_locale: str | None = None,
    execution_environment_note: str | None = None,
    *,
    cloud_tool_root: str | None = None,
    account_personalization: dict[str, str] | None = None,
    composio_section: str | None = None,
    learned_memory_prefetch: str | None = None,
) -> str:
    return build_tiered_system_prompt(
        workspace,
        client_timezone=client_timezone,
        client_locale=client_locale,
        execution_environment_note=execution_environment_note,
        cloud_tool_root=cloud_tool_root,
        account_personalization=account_personalization,
        composio_section=composio_section,
        learned_memory_prefetch=learned_memory_prefetch,
    )


class Agent:
    """Anthropic-style agent loop: model chooses tools vs final text every turn."""

    def __init__(self) -> None:
        self._llm_by_provider: dict[str, UnifiedLLMClient] = {}
        self.context_manager = ContextManager(
            max_messages=28,
            summarize_after=14,
            max_tool_result_chars=max(4_000, int(settings.max_tool_result_chars)),
            compact_tool_rounds=bool(settings.chat_compact_tool_context),
        )

    async def _setup_active_tools(
        self,
        composio_registry_token: list[Any],
        emit: Callable[[dict[str, Any]], None],
        *,
        execution_target: str,
        blaxel_sandbox_active: bool,
        run_context: AgentRunContext | None = None,
        task_class: str = "standard",
    ) -> list[Any]:
        """Initialize tools and integrate Composio if configured."""
        extra_tools: list[Any] = list(run_context.extra_tools) if run_context and run_context.extra_tools else []
        active_tools = list(
            tools_for_execution_target(execution_target, blaxel_sandbox_active=blaxel_sandbox_active)
        )
        composio_sub = bool(settings.composio_subagent_mode)
        if composio_runtime.is_configured():
            try:
                if composio_sub:
                    active_tools = active_tools + [COMPOSIO_RUN_TOOL]
                else:
                    comp = await asyncio.to_thread(composio_runtime.build_dynamic_composio_tools)
                    composio_registry_token[0] = composio_runtime.push_composio_tool_registry(comp)
                    active_tools = active_tools + comp
            except Exception as e:
                msg = redact_secrets(str(e))
                log.warning("composio dynamic tools skipped: %s", msg)
                emit({"type": "agent.warning", "data": {"composio": f"Could not load Composio tools: {msg}"}})
        active_tools = tools_for_dispatcher_turn(
            active_tools,
            task_class=task_class,
            composio_subagent_mode=composio_sub,
        )
        if extra_tools:
            seen = {t.name for t in active_tools}
            for t in extra_tools:
                if t.name not in seen:
                    active_tools.append(t)
                    seen.add(t.name)
        return active_tools

    def _llm(self, provider_id: str) -> UnifiedLLMClient:
        pid = provider_id.strip().lower()
        if pid not in self._llm_by_provider:
            self._llm_by_provider[pid] = UnifiedLLMClient(provider_override=pid)
        return self._llm_by_provider[pid]

    async def run(
        self,
        user_input: str,
        session: SessionState,
        emit: Callable[[dict[str, Any]], None],
        workspace: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        client_timezone: str | None = None,
        client_locale: str | None = None,
        image_parts: list[dict[str, str]] | None = None,
        max_steps_override: int | None = None,
        run_context: AgentRunContext | None = None,
        cloud_sandbox: Any | None = None,
        account_personalization: dict[str, str] | None = None,
        *,
        run_id: str | None = None,
        cancel_event: asyncio.Event | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        composio_registry_token: list[Any] = [None]
        try:
            async with _AGENT_RUN_SEMAPHORE:
                async for row in self._run_agent_turn(
                    user_input,
                    session,
                    emit,
                    workspace,
                    model,
                    provider,
                    client_timezone,
                    client_locale,
                    image_parts,
                    composio_registry_token,
                    max_steps_override=max_steps_override,
                    run_context=run_context,
                    cloud_sandbox=cloud_sandbox,
                    account_personalization=account_personalization,
                    run_id=run_id,
                    cancel_event=cancel_event,
                ):
                    yield row
        finally:
            composio_runtime.reset_composio_tool_registry(composio_registry_token[0])

    async def _run_agent_turn(
        self,
        user_input: str,
        session: SessionState,
        emit: Callable[[dict[str, Any]], None],
        workspace: str | None,
        model: str | None,
        provider: str | None,
        client_timezone: str | None,
        client_locale: str | None,
        image_parts: list[dict[str, str]] | None,
        composio_registry_token: list[Any],
        max_steps_override: int | None = None,
        run_context: AgentRunContext | None = None,
        cloud_sandbox: Any | None = None,
        account_personalization: dict[str, str] | None = None,
        *,
        run_id: str | None = None,
        cancel_event: asyncio.Event | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        from koraku.integrations.blaxel_lazy import lazy_blaxel_session_active
        from koraku.integrations.blaxel_runtime import cloud_blaxel_block_reason

        ws = resolve_agent_workspace(workspace, run_context)
        execution_target = resolve_execution_target(run_context)
        exec_tok = bind_execution_target(execution_target)
        blaxel_lazy = (
            execution_target == "cloud"
            and lazy_blaxel_session_active()
            and cloud_blaxel_block_reason(settings) is None
        )
        blaxel_active = cloud_sandbox is not None or blaxel_lazy
        env_note: str | None = None
        session_root: str | None = None
        blaxel_root_override = (
            (run_context.blaxel_session_root or "").strip() if run_context else None
        ) or None
        if cloud_sandbox is not None or blaxel_lazy:
            session_root = resolve_blaxel_session_root(
                session.session_id,
                settings,
                override_root=blaxel_root_override,
            )
        if cloud_sandbox is not None:
            try:
                sname = cloud_sandbox.metadata.name
            except Exception:
                sname = "sandbox"
            scope_label = (
                "iMessage workspace"
                if blaxel_root_override and "/imessage/" in blaxel_root_override
                else "this chat's folder"
            )
            env_note = (
                f"- **Blaxel sandbox `{sname}`** (one VM per user): **Read**, **Write**, **Edit**, **Bash**, "
                f"**Glob**, and **Grep** run under {scope_label} `{session_root}`. "
                "Use paths relative to that folder (e.g. `notes.md`, `todo.txt`)."
            )
        elif blaxel_lazy and session_root:
            env_note = (
                f"- **Blaxel sandbox** (lazy attach): **Read**, **Write**, **Edit**, **Bash**, **Glob**, and **Grep** "
                f"use this chat's folder `{session_root}`. The VM connects on the first file/shell tool call."
            )
        elif execution_target == "cloud" and cloud_blaxel_block_reason(settings):
            env_note = cloud_blaxel_block_reason(settings)
        try:
            with (
                agent_workspace_scope(ws),
                blaxel_sandbox_scope(cloud_sandbox),
                blaxel_session_workspace_scope(session_root),
            ):
                composio_runtime.configure_workspace_cache(ws)
                eff_provider = resolve_provider_id(provider)
                effective_model = resolve_effective_model(model, provider_id=eff_provider)
                imgs = list(image_parts or [])
                budget_text = user_input.strip() or ("[images]" if imgs else "")
                mode, turn_limits = resolve_turn_limits(budget_text, max_steps_override)

                mode_event = {
                    "type": "agent.mode",
                    "data": {
                        "mode": mode,
                        "max_steps": turn_limits.max_rounds,
                        "wall_seconds": turn_limits.wall_seconds,
                        "task_class": turn_limits.task_class,
                        "dispatcher_mode": dispatcher_mode_active(),
                        "model": effective_model,
                        "provider": eff_provider,
                        "session_id": session.session_id,
                        "run_id": run_id or "",
                        "execution_target": execution_target,
                        "blaxel_sandbox": blaxel_active,
                    },
                }
                emit(mode_event)
                yield mode_event

                active_tools = await self._setup_active_tools(
                    composio_registry_token,
                    emit,
                    execution_target=execution_target,
                    blaxel_sandbox_active=blaxel_active,
                    run_context=run_context,
                    task_class=turn_limits.task_class,
                )
                tool_names = [t.name for t in active_tools]
                tools_event = {"type": "agent.tools", "data": {"tools": tool_names, "count": len(tool_names)}}
                emit(tools_event)
                yield tools_event

                delegate_tok: Any = None
                if composio_runtime.is_configured() and bool(settings.composio_subagent_mode):
                    delegate_tok = set_composio_delegate_context(
                        ComposioDelegateContext(
                            agent=self,
                            emit=emit,
                            session=session,
                            workspace=ws,
                            model=model,
                            provider=provider,
                            client_timezone=client_timezone,
                            client_locale=client_locale,
                            execution_target=execution_target,
                            blaxel_sandbox_active=blaxel_active,
                            run_context=run_context,
                            cloud_sandbox=cloud_sandbox,
                            account_personalization=account_personalization,
                            run_id=run_id,
                            cancel_event=cancel_event,
                        )
                    )
                try:
                    user_turn = build_user_message_blocks(user_input, imgs)
                    session.add_message("user", user_turn)
                    session.step_count = 0
                    if composio_runtime.is_configured():
                        if bool(settings.composio_subagent_mode):
                            composio_sec = await asyncio.to_thread(
                                composio_runtime.composio_dispatcher_prompt_section
                            )
                        else:
                            composio_sec = await asyncio.to_thread(
                                composio_runtime.composio_system_prompt_section
                            )
                    else:
                        composio_sec = None
                    learned_prefetch = await prefetch_learned_memory_volatile(user_input, workspace=ws)
                    system_prompt = build_system_prompt(
                        ws,
                        client_timezone=client_timezone,
                        client_locale=client_locale,
                        execution_environment_note=env_note,
                        cloud_tool_root=session_root if blaxel_active else None,
                        account_personalization=account_personalization,
                        composio_section=composio_sec,
                        learned_memory_prefetch=learned_prefetch,
                    )
                    dispatch_appendix = dispatcher_system_appendix(turn_limits.task_class)
                    if dispatch_appendix:
                        system_prompt = f"{system_prompt.rstrip()}\n\n{dispatch_appendix.lstrip()}"
                    ctx_appendix = (
                        (run_context.system_appendix or "").strip() if run_context else ""
                    )
                    if ctx_appendix:
                        system_prompt = f"{system_prompt.rstrip()}\n\n{ctx_appendix}"
                    working_memory: list[dict[str, Any]] = []
                    async for ev in self._iterate_react_steps(
                        session=session,
                        emit=emit,
                        active_tools=active_tools,
                        system_prompt=system_prompt,
                        working_memory=working_memory,
                        effective_model=effective_model,
                        eff_provider=eff_provider,
                        mode=mode,
                        limits=turn_limits,
                        cancel_event=cancel_event,
                        run_id=run_id,
                        context_manager=self.context_manager,
                    ):
                        yield ev
                finally:
                    if delegate_tok is not None:
                        reset_composio_delegate_context(delegate_tok)
        finally:
            reset_execution_target(exec_tok)

    async def _synthesize_final_reply(
        self,
        *,
        session: SessionState,
        emit: Callable[[dict[str, Any]], None],
        system_prompt: str,
        effective_model: str,
        eff_provider: str,
        context_manager: ContextManager,
        steering_user: str,
        reason: str,
        mode: str,
        run_id: str | None,
    ) -> AsyncIterator[dict[str, Any]]:
        """One no-tools LLM call so budget/loop exits still return user-facing text."""
        session.add_message("user", steering_user)
        context_messages = context_manager.process_messages(session.messages)
        assistant_content: list[dict[str, Any]] = []
        llm_stream = self._llm(eff_provider).stream(
            messages=context_messages,
            tool_schemas=[],
            system_prompt=system_prompt,
            model=effective_model,
        )
        async for event in llm_stream:
            wrapped = {"type": "stream_event", "event": event}
            emit(wrapped)
            yield wrapped
            if event.get("type") == "assistant_message":
                assistant_content = event["message"]["content"]
        session.add_message("assistant", assistant_content, model=effective_model, stop_reason="end_turn")
        done = {
            "type": "agent.completed",
            "data": {
                "reason": reason,
                "steps": session.step_count,
                "mode": mode,
                "provider": eff_provider,
                "model": effective_model,
                "run_id": run_id or "",
            },
        }
        emit(done)
        yield done

    async def _iterate_react_steps(
        self,
        *,
        session: SessionState,
        emit: Callable[[dict[str, Any]], None],
        active_tools: list[Any],
        system_prompt: str,
        working_memory: list[dict[str, Any]],
        effective_model: str,
        eff_provider: str,
        mode: str,
        limits: TurnLimits,
        cancel_event: asyncio.Event | None,
        run_id: str | None,
        context_manager: ContextManager,
    ) -> AsyncIterator[dict[str, Any]]:
        loop_tracker = LoopTracker()
        max_rounds = limits.max_rounds
        budget_steering_sent = False
        while session.step_count < max_rounds:
            if limits.wall_exhausted():
                session.step_count += 1
                async for ev in self._synthesize_final_reply(
                    session=session,
                    emit=emit,
                    system_prompt=system_prompt,
                    effective_model=effective_model,
                    eff_provider=eff_provider,
                    context_manager=context_manager,
                    steering_user=BUDGET_EXHAUSTED_USER,
                    reason="wall_clock_exhausted",
                    mode=mode,
                    run_id=run_id,
                ):
                    yield ev
                return

            session.step_count += 1
            if cancel_event is not None and cancel_event.is_set():
                ce = {
                    "type": "agent.cancelled",
                    "data": {
                        "reason": "client_disconnect",
                        "run_id": run_id or "",
                        "steps": session.step_count,
                        "model": effective_model,
                        "provider": eff_provider,
                    },
                }
                emit(ce)
                yield ce
                return

            context_messages = context_manager.process_messages(session.messages)
            working_memory_context = format_working_memory_context(working_memory)
            if working_memory_context is not None:
                context_messages = [*context_messages, working_memory_context]
            if (
                not budget_steering_sent
                and session.step_count >= limits.warn_rounds
                and not limits.wall_exhausted()
            ):
                budget_steering_sent = True
                context_messages = [
                    *context_messages,
                    AgentMessage(role="user", content=BUDGET_STEERING_USER),
                ]
            token_estimate = context_manager.estimate_tokens(context_messages)
            ctx_event = {
                "type": "agent.context",
                "data": {"messages": len(context_messages), "estimated_tokens": token_estimate},
            }
            emit(ctx_event)
            yield ctx_event

            assistant_content: list[dict[str, Any]] = []
            tool_uses: list[dict[str, Any]] = []

            llm_stream = self._llm(eff_provider).stream(
                messages=context_messages,
                tool_schemas=active_tools,
                system_prompt=system_prompt,
                model=effective_model,
            )
            stream_it = llm_stream.__aiter__()
            t_deadline = time.monotonic() + max(30.0, float(settings.agent_llm_stream_timeout_seconds))
            llm_timed_out = False
            hb_iv = max(5.0, float(settings.agent_llm_stream_heartbeat_seconds))
            last_progress = time.monotonic()
            while True:
                if cancel_event is not None and cancel_event.is_set():
                    break
                if time.monotonic() - last_progress >= hb_iv:
                    _emit_worker_status(emit, "Still working…", phase="llm")
                    last_progress = time.monotonic()
                remaining = t_deadline - time.monotonic()
                if remaining <= 0:
                    llm_timed_out = True
                    log.warning(
                        "agent llm stream wall timeout session_id=%s run_id=%s provider=%s model=%s",
                        session.session_id,
                        run_id or "",
                        eff_provider,
                        effective_model,
                    )
                    break
                try:
                    event = await asyncio.wait_for(
                        stream_it.__anext__(),
                        timeout=min(120.0, max(0.5, remaining)),
                    )
                except StopAsyncIteration:
                    break
                except asyncio.TimeoutError:
                    llm_timed_out = True
                    log.warning(
                        "agent llm stream chunk timeout session_id=%s run_id=%s provider=%s",
                        session.session_id,
                        run_id or "",
                        eff_provider,
                    )
                    break
                last_progress = time.monotonic()
                wrapped = {"type": "stream_event", "event": event}
                emit(wrapped)
                yield wrapped

                if event["type"] == "assistant_message":
                    assistant_content = event["message"]["content"]

            if llm_timed_out:
                err = {
                    "type": "agent.error",
                    "data": {
                        "error": (
                            "The model took too long to finish this step. "
                            "Try a shorter question, a smaller scope, or again in a moment."
                        ),
                        "code": "llm_stream_timeout",
                        "run_id": run_id or "",
                    },
                }
                emit(err)
                yield err
                return

            if cancel_event is not None and cancel_event.is_set():
                ce = {
                    "type": "agent.cancelled",
                    "data": {
                        "reason": "client_disconnect",
                        "run_id": run_id or "",
                        "steps": session.step_count,
                        "model": effective_model,
                        "provider": eff_provider,
                    },
                }
                emit(ce)
                yield ce
                return

            for block in assistant_content:
                if block.get("type") == "tool_use":
                    tool_uses.append(block)

            if not tool_uses:
                session.add_message("assistant", assistant_content, model=effective_model, stop_reason="end_turn")
                done = {
                    "type": "agent.completed",
                    "data": {
                        "reason": "end_turn",
                        "steps": session.step_count,
                        "mode": mode,
                        "provider": eff_provider,
                        "model": effective_model,
                    },
                }
                emit(done)
                yield done
                return

            session.add_message("assistant", assistant_content, model=effective_model, stop_reason="tool_use")

            set_active_session(session)
            try:
                tool_results = await asyncio.wait_for(
                    self._execute_tools_parallel(tool_uses, emit, active_tools),
                    timeout=max(30.0, float(settings.agent_tool_phase_timeout_seconds)),
                )
            except asyncio.TimeoutError:
                log.warning(
                    "agent tool phase timeout session_id=%s run_id=%s tools=%s",
                    session.session_id,
                    run_id or "",
                    [tu.get("name") for tu in tool_uses],
                )
                tool_results = [
                    {
                        "type": "tool_result",
                        "tool_use_id": tu["id"],
                        "content": (
                            f"Error: Tool execution exceeded "
                            f"{int(settings.agent_tool_phase_timeout_seconds)}s for this step."
                        ),
                        "is_error": True,
                    }
                    for tu in tool_uses
                ]
            finally:
                set_active_session(None)

            for tr in tool_results:
                result_event = {
                    "type": "user",
                    "message": {"role": "user", "content": [tr]},
                }
                emit(result_event)
                yield result_event

            session.add_message("user", tool_results)

            loop_tracker.record(tool_uses)
            if loop_tracker.has_repeat():
                session.add_message("user", LOOP_STEERING_USER)

            self._update_memory(working_memory, tool_results)
            if working_memory:
                mem_ev = {"type": "agent.memory", "data": {"findings": len(working_memory)}}
                emit(mem_ev)
                yield mem_ev

        if limits.synthesize_on_exhaust:
            async for ev in self._synthesize_final_reply(
                session=session,
                emit=emit,
                system_prompt=system_prompt,
                effective_model=effective_model,
                eff_provider=eff_provider,
                context_manager=context_manager,
                steering_user=BUDGET_EXHAUSTED_USER,
                reason="max_rounds_reached",
                mode=mode,
                run_id=run_id,
            ):
                yield ev
            return

        done = {
            "type": "agent.completed",
            "data": {
                "reason": "max_steps_reached",
                "steps": session.step_count,
                "mode": mode,
                "provider": eff_provider,
                "model": effective_model,
            },
        }
        emit(done)
        yield done

    async def _execute_composio_subagent(
        self,
        *,
        toolkits: list[str],
        goal: str,
        max_steps_override: int | None = None,
    ) -> str:
        from koraku.agent.composio_delegate_context import get_composio_delegate_context

        ctx = get_composio_delegate_context()
        if ctx is None:
            return "Error: ComposioRun invoked without active delegate context."
        if not composio_runtime.is_configured():
            return "Error: Composio is not configured."
        if not goal.strip():
            return "Error: `goal` must be a non-empty string."

        comp_tools = await asyncio.to_thread(composio_runtime.build_dynamic_composio_tools_for_toolkits, toolkits)
        if not comp_tools:
            active = ", ".join(composio_runtime.active_toolkit_slugs()) or "(none)"
            return (
                "Error: No Composio tools loaded for those toolkits. "
                f"Each slug must be ACTIVE in Connections. Active now: {active}."
            )

        inner_registry_tok: Any = None
        try:
            inner_registry_tok = composio_runtime.push_composio_tool_registry(comp_tools)
        except Exception as e:
            return f"Error: could not register Composio tools: {redact_secrets(str(e))}"

        sub_session_id = f"{ctx.session.session_id}:composio"
        sub_session = SessionState(session_id=sub_session_id)
        sub_cm = ContextManager(
            max_messages=24,
            summarize_after=14,
            max_tool_result_chars=self.context_manager.max_tool_result_chars,
            compact_tool_rounds=self.context_manager.compact_tool_rounds,
        )

        base = [
            t
            for t in tools_for_execution_target(
                ctx.execution_target,
                blaxel_sandbox_active=ctx.blaxel_sandbox_active,
            )
            if t.name != "ComposioRun"
        ]
        goal_class = classify_composio_goal(goal)
        active_sub = tools_for_composio_worker(base, comp_tools, goal)
        eff_provider = resolve_provider_id(ctx.provider)
        effective_model = resolve_effective_model(ctx.model, provider_id=eff_provider)
        max_sub = composio_max_rounds_for_goal(goal, override=max_steps_override)
        sub_limits = TurnLimits(
            task_class=goal_class,
            max_rounds=max_sub,
            wall_seconds=composio_wall_seconds_for_goal(goal),
            started_monotonic=time.monotonic(),
        )

        session_root: str | None = None
        if ctx.cloud_sandbox is not None:
            try:
                override = (
                    (ctx.run_context.blaxel_session_root or "").strip()
                    if ctx.run_context
                    else None
                ) or None
                session_root = resolve_blaxel_session_root(
                    ctx.session.session_id,
                    settings,
                    override_root=override,
                )
            except Exception:
                session_root = None
        env_note: str | None = None
        if ctx.cloud_sandbox is not None and session_root:
            env_note = (
                f"- **Blaxel sandbox** (this chat): **Read**, **Write**, **Edit**, **Bash**, "
                f"**Glob**, **Grep** under `{session_root}`."
            )

        tk_seen: set[str] = set()
        for t in comp_tools:
            cats = t.categories or []
            if len(cats) > 1:
                tk_seen.add(str(cats[1]).upper())
        scoped_for_prompt = sorted(tk_seen)

        system_prompt = build_composio_subagent_system_prompt(
            ctx.workspace,
            scoped_for_prompt,
            client_timezone=ctx.client_timezone,
            client_locale=ctx.client_locale,
            execution_environment_note=env_note,
            cloud_tool_root=session_root if ctx.cloud_sandbox is not None else None,
            goal_class=goal_class,
        )
        sub_session.add_message("user", goal.strip())
        sub_session.step_count = 0

        def nested_emit(ev: dict[str, Any]) -> None:
            ctx.emit(
                {
                    **ev,
                    "subagent": {"composio": True, "toolkits": list(scoped_for_prompt)},
                }
            )

        nested_emit({"type": "agent.subagent", "data": {"phase": "composio_start", "toolkits": scoped_for_prompt}})
        last_reason: str | None = None
        try:
            async for ev in self._iterate_react_steps(
                session=sub_session,
                emit=nested_emit,
                active_tools=active_sub,
                system_prompt=system_prompt,
                working_memory=[],
                effective_model=effective_model,
                eff_provider=eff_provider,
                mode="composio_sub",
                limits=sub_limits,
                cancel_event=ctx.cancel_event,
                run_id=ctx.run_id,
                context_manager=sub_cm,
            ):
                if ev.get("type") == "agent.completed":
                    d = ev.get("data")
                    if isinstance(d, dict):
                        last_reason = str(d.get("reason") or "") or last_reason
        finally:
            composio_runtime.reset_composio_tool_registry(inner_registry_tok)

        nested_emit({"type": "agent.subagent", "data": {"phase": "composio_end", "toolkits": scoped_for_prompt}})
        out = _subagent_final_assistant_text(sub_session)
        if last_reason == "max_steps_reached":
            out += "\n\n(Integration worker stopped at max steps; retry with a narrower goal or higher max_steps.)"
        return out

    def _update_memory(self, memory: list[dict[str, Any]], tool_results: list[dict[str, Any]]) -> None:
        for tr in tool_results:
            summary = _tool_result_summary(tr)
            if summary is not None:
                memory.append(summary)
        if len(memory) > _WORKING_MEMORY_MAX_ITEMS * 2:
            del memory[:-_WORKING_MEMORY_MAX_ITEMS * 2]

    async def _execute_tools_parallel(
        self,
        tool_uses: list[dict[str, Any]],
        emit: Callable[[dict[str, Any]], None],
        active_tools: list[Any],
    ) -> list[dict[str, Any]]:
        for tool_use in tool_uses:
            exec_event = {
                "type": "tool_execution",
                "data": {
                    "tool": tool_use["name"],
                    "input": tool_use["input"],
                    "id": tool_use["id"],
                    "mode": "parallel" if len(tool_uses) > 1 else "sequential",
                },
            }
            emit(exec_event)

        names = [str(tu.get("name") or "tool") for tu in tool_uses]
        primary_tool = names[0] if names else None
        hb_iv = max(3.0, float(settings.agent_worker_heartbeat_seconds))
        stop_hb = asyncio.Event()

        async def _tool_heartbeat() -> None:
            while not stop_hb.is_set():
                try:
                    await asyncio.wait_for(stop_hb.wait(), timeout=hb_iv)
                except asyncio.TimeoutError:
                    if len(names) == 1:
                        msg = f"Running {names[0]}…"
                    else:
                        msg = f"Running {len(names)} tools…"
                    _emit_worker_status(emit, msg, tool_name=primary_tool, phase="tools")

        hb_task = asyncio.create_task(_tool_heartbeat())
        try:
            if len(tool_uses) == 1:
                return [await self._execute_single_tool(tool_uses[0], active_tools)]

            async def run_one(tu: dict[str, Any]) -> dict[str, Any]:
                return await self._execute_single_tool(tu, active_tools)

            results = await asyncio.gather(*[run_one(tu) for tu in tool_uses], return_exceptions=True)
            processed: list[dict[str, Any]] = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed.append({
                        "type": "tool_result",
                        "tool_use_id": tool_uses[i]["id"],
                        "content": f"Error: {result}",
                        "is_error": True,
                    })
                else:
                    processed.append(result)
            return processed
        finally:
            stop_hb.set()
            hb_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await hb_task

    async def _execute_single_tool(
        self,
        tool_use: dict[str, Any],
        active_tools: list[Any],
        max_retries: int = 2,
    ) -> dict[str, Any]:
        tool_name = tool_use["name"]
        tool_input = tool_use["input"]
        tool_id = tool_use["id"]

        if isinstance(tool_input, dict) and "_partial_json" in tool_input:
            return {
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": (
                    f"Error: Tool '{tool_name}' arguments were truncated (incomplete JSON). "
                    "Retry with a shorter payload or split large writes into smaller chunks."
                ),
                "is_error": True,
            }

        tool = _resolve_tool_from_active(tool_name, active_tools)
        if tool is None:
            return {
                "type": "tool_result", "tool_use_id": tool_id,
                "content": f"Error: Tool '{tool_name}' not found.", "is_error": True,
            }

        last_error = ""
        for attempt in range(max_retries + 1):
            try:
                async with _TOOL_RUN_SEMAPHORE:
                    result_text = await tool.run(**tool_input)
                is_error = tool_stdout_indicates_error(result_text, tool_name=tool_name)
                if not is_error:
                    return {"type": "tool_result", "tool_use_id": tool_id, "content": result_text, "is_error": False}
                last_error = result_text
                if attempt < max_retries:
                    await asyncio.sleep(0.5 * (attempt + 1))
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries:
                    await asyncio.sleep(0.5 * (attempt + 1))

        return {
            "type": "tool_result", "tool_use_id": tool_id,
            "content": f"{last_error} (failed after {max_retries + 1} attempts)", "is_error": True,
        }
