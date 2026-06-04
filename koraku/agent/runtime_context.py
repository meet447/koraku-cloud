"""Execution context for a single agent run (workspace + tool policy)."""
from __future__ import annotations

import os
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from koraku.workspace.paths import workspace_dir

if TYPE_CHECKING:
    from koraku.tools.tool_def import Tool

ExecutionTarget = Literal["local", "server", "cloud"]
ChatExecutionMode = ExecutionTarget

_active_execution_target: ContextVar[ExecutionTarget | None] = ContextVar(
    "koraku_execution_target",
    default=None,
)


def resolve_agent_workspace(
    workspace: str | None,
    run_context: "AgentRunContext | None",
) -> str:
    """Effective workspace directory for this turn (explicit arg wins, then context, then cwd)."""
    if workspace is not None:
        return os.path.abspath(workspace)
    if run_context is not None and run_context.workspace_root:
        return os.path.abspath(run_context.workspace_root)
    return workspace_dir()


def resolve_execution_target(run_context: "AgentRunContext | None") -> ExecutionTarget:
    if run_context is not None:
        return run_context.execution_target
    from koraku.core.config import get_settings

    return get_settings().default_execution_target  # type: ignore[return-value]


def get_active_execution_target() -> ExecutionTarget | None:
    return _active_execution_target.get()


def bind_execution_target(target: ExecutionTarget) -> Token[ExecutionTarget | None]:
    return _active_execution_target.set(target)


def reset_execution_target(token: Token[ExecutionTarget | None]) -> None:
    _active_execution_target.reset(token)


@dataclass(frozen=True)
class AgentRunContext:
    """Binds one turn to a workspace root and tool policy."""

    workspace_root: str | None = None
    execution_target: ExecutionTarget = "local"
    extra_tools: tuple["Tool", ...] = field(default_factory=tuple)
    system_appendix: str | None = None
    #: When set (e.g. iMessage), file tools use this VM folder instead of ``sessions/{id}/``.
    blaxel_session_root: str | None = None
