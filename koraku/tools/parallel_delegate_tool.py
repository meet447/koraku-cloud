"""ParallelRun — fan out independent research/code/composio subtasks."""
from __future__ import annotations

from koraku.agent.composio_delegate_context import get_composio_delegate_context
from koraku.tools.tool_def import Tool


async def _parallel_run_handler(tasks: list[dict]) -> str:
    ctx = get_composio_delegate_context()
    if ctx is None:
        return "Error: ParallelRun is only available during an active chat turn."
    agent = ctx.agent
    fn = getattr(agent, "_execute_parallel_run", None)
    if fn is None:
        return "Error: ParallelRun is not wired (internal)."
    return await fn(tasks=list(tasks or []))


PARALLEL_RUN_TOOL = Tool(
    name="ParallelRun",
    description=(
        "Run up to 3 independent subtasks in parallel and merge results. "
        "Each task needs `kind` and `goal`. "
        "Kinds: `research`, `code`, `document`, `presentation`, `spreadsheet`, or `composio`. "
        "Composio tasks also need `toolkits` (uppercase slugs). "
        "After ResearchRun, batch doc + deck + chart PNG work here (document + presentation + code) "
        "instead of serial DocumentRun/PresentationRun/CodeRun."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "tasks": {
                "type": "array",
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "kind": {
                            "type": "string",
                            "enum": [
                                "research",
                                "code",
                                "composio",
                                "document",
                                "presentation",
                                "spreadsheet",
                            ],
                        },
                        "goal": {"type": "string"},
                        "toolkits": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["kind", "goal"],
                },
            },
        },
        "required": ["tasks"],
    },
    handler=_parallel_run_handler,
    categories=["delegate", "parallel"],
)
