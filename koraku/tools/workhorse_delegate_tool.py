"""ResearchRun, CodeRun, and VerifyGoal delegate tools."""
from __future__ import annotations

from koraku.agent.composio_delegate_context import get_composio_delegate_context
from koraku.tools.tool_def import Tool


async def _research_run_handler(goal: str, max_steps: int | None = None) -> str:
    ctx = get_composio_delegate_context()
    if ctx is None:
        return "Error: ResearchRun is only available during an active chat turn."
    agent = ctx.agent
    fn = getattr(agent, "_execute_research_subagent", None)
    if fn is None:
        return "Error: Research sub-agent execution is not wired (internal)."
    return await fn(goal=(goal or "").strip(), max_steps_override=max_steps)


async def _code_run_handler(goal: str, max_steps: int | None = None) -> str:
    ctx = get_composio_delegate_context()
    if ctx is None:
        return "Error: CodeRun is only available during an active chat turn."
    agent = ctx.agent
    fn = getattr(agent, "_execute_code_subagent", None)
    if fn is None:
        return "Error: Code sub-agent execution is not wired (internal)."
    return await fn(goal=(goal or "").strip(), max_steps_override=max_steps)


async def _verify_goal_handler(criteria: str, evidence: str = "") -> str:
    ctx = get_composio_delegate_context()
    if ctx is None:
        return "Error: VerifyGoal is only available during an active chat turn."
    agent = ctx.agent
    fn = getattr(agent, "_execute_verify_goal", None)
    if fn is None:
        return "Error: VerifyGoal is not wired (internal)."
    return await fn(criteria=(criteria or "").strip(), evidence=(evidence or "").strip())


RESEARCH_RUN_TOOL = Tool(
    name="ResearchRun",
    description=(
        "Spawn a **research worker** for multi-step web investigation: parallel **WebSearch**, "
        "**WebFetch**, and synthesis. Pass a focused `goal` (not the full chat transcript)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "goal": {"type": "string", "description": "Research question and success criteria."},
            "max_steps": {"type": "integer", "description": "Optional max ReAct steps for this sub-run."},
        },
        "required": ["goal"],
    },
    handler=_research_run_handler,
    categories=["research", "delegate"],
)

CODE_RUN_TOOL = Tool(
    name="CodeRun",
    description=(
        "Spawn a **code worker** in the Blaxel sandbox for scripts, file edits, tests, and data work. "
        "Requires cloud execution with an active sandbox."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "goal": {"type": "string", "description": "Coding task, paths, and verification steps."},
            "max_steps": {"type": "integer", "description": "Optional max ReAct steps for this sub-run."},
        },
        "required": ["goal"],
    },
    handler=_code_run_handler,
    categories=["code", "delegate"],
)

VERIFY_GOAL_TOOL = Tool(
    name="VerifyGoal",
    description=(
        "Check whether completed work meets stated success criteria before telling the user the task is done. "
        "Returns PASS or FAIL with gaps to fix."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "criteria": {"type": "string", "description": "What must be true for success."},
            "evidence": {
                "type": "string",
                "description": "Summary of actions taken, tool outputs, paths, or counts.",
            },
        },
        "required": ["criteria"],
    },
    handler=_verify_goal_handler,
    categories=["verify", "delegate"],
)

WORKHORSE_RUN_TOOLS: list[Tool] = [RESEARCH_RUN_TOOL, CODE_RUN_TOOL, VERIFY_GOAL_TOOL]
