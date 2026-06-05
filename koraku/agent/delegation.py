"""Subagent delegation mixin for the Koraku agent."""
from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

from koraku.core.config import settings
from koraku.core.redact import redact_secrets
from koraku.core.models import SessionState
from koraku.agent.context_manager import ContextManager
from koraku.llm.catalog import resolve_effective_model, resolve_provider_id
from koraku.tools.registry import tools_for_execution_target
from koraku.integrations import composio as composio_runtime
from koraku.agent.composio_delegate_context import get_composio_delegate_context
from koraku.integrations.artifact_prompt import (
    artifact_subagent_mode_active,
    build_artifact_subagent_system_prompt,
)
from koraku.integrations.blaxel_runtime import resolve_blaxel_session_root
from koraku.tools.blaxel_dispatch import format_blaxel_sandbox_execution_guide
from koraku.agent.prompt_sections import format_runtime_context_section
from koraku.agent.budget import (
    TurnLimits,
    composio_max_rounds_for_goal,
    composio_wall_seconds_for_goal,
    composio_worker_sop_appendix,
    classify_composio_goal,
    classify_artifact_goal,
    artifact_max_rounds_for_goal,
    artifact_wall_seconds_for_goal,
    tools_for_artifact_worker,
    tools_for_composio_worker,
)

log = logging.getLogger(__name__)


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


class SubagentDelegationMixin:
    async def _execute_composio_subagent(
        self,
        *,
        toolkits: list[str],
        goal: str,
        max_steps_override: int | None = None,
    ) -> str:
        ctx = get_composio_delegate_context()
        if ctx is None:
            return "Execution failure: Integration block triggered outside localized runtime scope context."
        if not composio_runtime.is_configured():
            return "Execution failure: Integration channel configurations are unmapped."
        if not goal.strip():
            return "Execution failure: Action description query criteria string must be non-empty."

        comp_tools = await asyncio.to_thread(composio_runtime.build_dynamic_composio_tools_for_toolkits, toolkits)
        if not comp_tools:
            active = ", ".join(composio_runtime.active_toolkit_slugs()) or "(none)"
            return (
                "Execution failure: No operational interfaces loaded for specified parameters. "
                f"Verify validation mapping parameters inside settings. Currently valid keys: {active}."
            )

        inner_registry_tok: Any = None
        try:
            inner_registry_tok = composio_runtime.push_composio_tool_registry(comp_tools)
        except Exception as e:
            return f"Execution failure: Mapping registry fault: {redact_secrets(str(e))}"

        sub_session_id = f"{ctx.session.session_id}:integration_run"
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
            env_note = format_blaxel_sandbox_execution_guide(session_root)

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
                    "subprocess_context": {"integration_active": True, "active_scopes": list(scoped_for_prompt)},
                }
            )

        nested_emit({"type": "agent.subagent", "data": {"subprocess_phase": "initialization", "active_scopes": scoped_for_prompt}})
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
                mode="integration_sub_loop",
                limits=sub_limits,
                cancel_event=ctx.cancel_event,
                run_id=ctx.run_id,
                context_manager=sub_cm,
            ):
                if ev.get("type") == "agent.completed":
                    d = ev.get("data")
                    if isinstance(d, dict):
                        last_reason = str(d.get("exit_reason") or "") or last_reason
        finally:
            composio_runtime.reset_composio_tool_registry(inner_registry_tok)

        nested_emit({"type": "agent.subagent", "data": {"subprocess_phase": "termination", "active_scopes": scoped_for_prompt}})
        out = _subagent_final_assistant_text(sub_session)
        if last_reason == "loop_allocation_ceiling_reached":
            out += "\n\n(Operation paused at maximum processing boundary checks.)"
        return out

    async def _execute_artifact_subagent(
        self,
        *,
        artifact_type: str,
        goal: str,
        max_steps_override: int | None = None,
    ) -> str:
        from koraku.agent.composio_delegate_context import get_composio_delegate_context
        from koraku.artifacts.sandbox_gate import require_sandbox_for_artifacts

        ctx = get_composio_delegate_context()
        if ctx is None:
            return "Error: ArtifactRun invoked without active delegate context."
        if not goal.strip():
            return "Error: `goal` must be a non-empty string."

        sandbox_err = await require_sandbox_for_artifacts()
        if sandbox_err:
            return sandbox_err

        valid_types = {"document", "presentation", "spreadsheet", "pdf"}
        atype = (artifact_type or "").strip().lower()
        if atype not in valid_types:
            return f"Error: unknown artifact_type {artifact_type!r}. Expected one of: {sorted(valid_types)}."

        sub_session_id = f"{ctx.session.session_id}:artifact:{atype}"
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
            if t.name not in {"ComposioRun", "DocumentRun", "PresentationRun", "SpreadsheetRun", "PdfRun"}
        ]
        goal_class = classify_artifact_goal(goal)
        active_sub = tools_for_artifact_worker(base, artifact_type=atype, goal=goal)
        if not active_sub:
            return "Error: No tools available for artifact worker in sandbox mode."

        eff_provider = resolve_provider_id(ctx.provider)
        effective_model = resolve_effective_model(ctx.model, provider_id=eff_provider)
        max_sub = artifact_max_rounds_for_goal(goal, override=max_steps_override)
        sub_limits = TurnLimits(
            task_class=goal_class,
            max_rounds=max_sub,
            wall_seconds=artifact_wall_seconds_for_goal(goal),
            started_monotonic=time.monotonic(),
        )

        session_root: str | None = None
        if ctx.cloud_sandbox is not None or ctx.blaxel_sandbox_active:
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
        if (ctx.cloud_sandbox is not None or ctx.blaxel_sandbox_active) and session_root:
            env_note = format_blaxel_sandbox_execution_guide(session_root)

        system_prompt = build_artifact_subagent_system_prompt(
            ctx.workspace,
            atype,
            client_timezone=ctx.client_timezone,
            client_locale=ctx.client_locale,
            execution_environment_note=env_note,
            cloud_tool_root=session_root if (ctx.cloud_sandbox is not None or ctx.blaxel_sandbox_active) else None,
            goal_class=goal_class,
        )
        sub_session.add_message("user", goal.strip())
        sub_session.step_count = 0

        def nested_emit(ev: dict[str, Any]) -> None:
            ctx.emit(
                {
                    **ev,
                    "subprocess_context": {"compilation_active": True, "format_target": atype},
                }
            )

        nested_emit({"type": "agent.subagent", "data": {"subprocess_phase": "compilation_start", "format_target": atype}})
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
                mode="compilation_sub_loop",
                limits=sub_limits,
                cancel_event=ctx.cancel_event,
                run_id=ctx.run_id,
                context_manager=sub_cm,
            ):
                if ev.get("type") == "agent.completed":
                    d = ev.get("data")
                    if isinstance(d, dict):
                        last_reason = str(d.get("exit_reason") or "") or last_reason
        finally:
            pass

        nested_emit({"type": "agent.subagent", "data": {"subprocess_phase": "compilation_end", "format_target": atype}})
        out = _subagent_final_assistant_text(sub_session)
        if last_reason == "loop_allocation_ceiling_reached":
            out += "\n\n(Compilation sequence paused at maximum operational safety checks.)"
        return out
