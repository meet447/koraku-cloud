"""Execution context for a single agent run (workspace + tool policy)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from koraku.workspace.paths import workspace_dir

if TYPE_CHECKING:
    from koraku.tools.tool_def import Tool

ExecutionTarget = Literal["cloud"]
ChatExecutionMode = Literal["cloud"]


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
    return "cloud"


@dataclass(frozen=True)
class AgentRunContext:
    """Binds one turn to a workspace root and tool policy (sandbox-only chat)."""

    workspace_root: str | None = None
    execution_target: ExecutionTarget = "cloud"
    extra_tools: tuple["Tool", ...] = field(default_factory=tuple)
