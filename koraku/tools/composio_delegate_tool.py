"""**ComposioRun** — dispatches a scoped Composio sub-agent with a minimal tool set per delegated goal."""
from __future__ import annotations

from koraku.agent.composio_delegate_context import get_composio_delegate_context
from koraku.tools.tool_def import Tool


async def _composio_run_handler(toolkits: list[str], goal: str, max_steps: int | None = None) -> str:
    ctx = get_composio_delegate_context()
    if ctx is None:
        return "Error: ComposioRun is only available during an active chat turn."
    agent = ctx.agent
    fn = getattr(agent, "_execute_composio_subagent", None)
    if fn is None:
        return "Error: Composio sub-agent execution is not wired (internal)."
    return await fn(toolkits=list(toolkits or []), goal=(goal or "").strip(), max_steps_override=max_steps)


COMPOSIO_RUN_TOOL = Tool(
    name="ComposioRun",
    description=(
        "Spawn a **scoped integration worker** that sees only Composio tools for the given `toolkits` "
        "(ACTIVE connection slugs such as GMAIL, GOOGLECALENDAR, GOOGLEDRIVE, SLACK). "
        "Use for real work in linked accounts: list mail, draft or send, calendar queries, Drive files, etc. "
        "Pass a clear `goal` for that worker (not the whole chat transcript). "
        "Prefer one toolkit per call when possible; use multiple slugs only when the task truly spans apps."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "toolkits": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Uppercase toolkit slugs; each must be ACTIVE under Connections.",
            },
            "goal": {
                "type": "string",
                "description": "Single-task instruction for the integration worker.",
            },
            "max_steps": {
                "type": "integer",
                "description": "Optional max ReAct steps for this sub-run (defaults to server setting).",
            },
        },
        "required": ["toolkits", "goal"],
    },
    handler=_composio_run_handler,
    categories=["composio", "delegate"],
)
