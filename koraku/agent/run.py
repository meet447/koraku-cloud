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
from koraku.tools.artifact_delegate_tool import ARTIFACT_RUN_TOOLS
from koraku.integrations.artifact_prompt import (
    artifact_subagent_mode_active,
)
from koraku.agent.blaxel_scope import blaxel_sandbox_scope, blaxel_session_workspace_scope
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
    dispatcher_mode_active,
    dispatcher_system_appendix,
    tools_for_dispatcher_turn,
    resolve_turn_limits,
)
from koraku.agent.utils import (
    build_user_message_blocks,
    _get_mode_and_budget,
    _step_budget,
    _snippet_text,
    _clean_one_line,
    _tool_result_summary,
    format_working_memory_context,
    _update_memory,
)
from koraku.agent.events import (
    _emit_llm_usage_estimate,
    _emit_worker_status,
)
from koraku.agent.tool_executor import ToolExecutionMixin
from koraku.agent.delegation import SubagentDelegationMixin

log = logging.getLogger(__name__)

_USER_SPECIFIC_MARKERS = re.compile(
    r"\b(my|me|i'm|i am|mine|our|we|remember when|last time|as i said|my name|call me)\b",
    re.I,
)

_AGENT_RUN_SEMAPHORE = asyncio.Semaphore(max(1, int(settings.agent_concurrency_limit)))


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


class Agent(SubagentDelegationMixin, ToolExecutionMixin):
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
        seen = {t.name for t in active_tools}
        if artifact_subagent_mode_active():
            for t in ARTIFACT_RUN_TOOLS:
                if t.name not in seen:
                    active_tools.append(t)
                    seen.add(t.name)
        for t in extra_tools:
            if t.name not in seen:
                active_tools.append(t)
                seen.add(t.name)
        return active_tools

    async def _composio_prompt_section_for_turn(self, task_class: str) -> str | None:
        if not composio_runtime.is_configured():
            return None
        if bool(settings.composio_subagent_mode):
            return await asyncio.to_thread(
                composio_runtime.composio_prompt_section_for_turn,
                task_class,
            )
        return await asyncio.to_thread(composio_runtime.composio_system_prompt_section)

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
        from koraku.integrations.blaxel_runtime import cloud_blaxel_block_reason, resolve_blaxel_session_root

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
        imessage_budget_tok = None
        if (
            settings.sendblue_api_key
            and settings.sendblue_api_secret
            and settings.sendblue_from_number
        ):
            from koraku_cloud.tools.imessage_send_tool import reset_imessage_send_budget

            imessage_budget_tok = reset_imessage_send_budget()
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

                active_tools, composio_sec, learned_prefetch = await asyncio.gather(
                    self._setup_active_tools(
                        composio_registry_token,
                        emit,
                        execution_target=execution_target,
                        blaxel_sandbox_active=blaxel_active,
                        run_context=run_context,
                        task_class=turn_limits.task_class,
                    ),
                    self._composio_prompt_section_for_turn(turn_limits.task_class),
                    prefetch_learned_memory_volatile(user_input, workspace=ws),
                )
                tool_names = [t.name for t in active_tools]
                tools_event = {"type": "agent.tools", "data": {"tools": tool_names, "count": len(tool_names)}}
                emit(tools_event)
                yield tools_event

                delegate_tok: Any = None
                needs_delegate = (composio_runtime.is_configured() and bool(settings.composio_subagent_mode)) or artifact_subagent_mode_active()
                if needs_delegate:
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
            if imessage_budget_tok is not None:
                from koraku_cloud.tools.imessage_send_tool import (
                    restore_imessage_send_budget,
                )

                restore_imessage_send_budget(imessage_budget_tok)
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
        yield _emit_llm_usage_estimate(
            emit,
            messages=context_messages,
            system_prompt=system_prompt,
            tool_schemas=[],
            assistant_content=assistant_content,
            model=effective_model,
            provider=eff_provider,
        )
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
            token_estimate = context_manager.estimate_tokens(
                context_messages,
                system_prompt=system_prompt,
                tool_schemas=active_tools,
            )
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

            yield _emit_llm_usage_estimate(
                emit,
                messages=context_messages,
                system_prompt=system_prompt,
                tool_schemas=active_tools,
                assistant_content=assistant_content,
                model=effective_model,
                provider=eff_provider,
            )

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

            _update_memory(working_memory, tool_results)
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
