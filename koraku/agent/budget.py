"""Turn budgets, task classification, and loop detection for the agent harness."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any

from koraku.core.config import settings
from koraku.tools.tool_def import Tool

# --- Turn task classes (drives wall-clock + round safety caps, not user-facing "modes") ---

_RESEARCH_MARKERS = (
    "research",
    "compare",
    "comparison",
    " vs ",
    "versus",
    "investigate",
    "comprehensive",
    "thorough",
    "analyze the project",
    "full stack",
    "end to end",
    "price",
    "pricing",
    "cost ",
    "cheapest",
    "best deal",
    "where to buy",
    "in stock",
    "availability",
    "retailer",
)

_COMPOSIO_SIMPLE_MARKERS = (
    "mark as read",
    "mark read",
    "unread",
    "inbox",
    "check email",
    "check mail",
    "any email",
    "read my email",
    "fetch email",
    "list email",
    "list message",
    "how many email",
    "calendar today",
    "what's on my calendar",
    "whats on my calendar",
    "upcoming event",
)

_COMPOSIO_COMPOSE_MARKERS = (
    "draft",
    "send email",
    "reply to",
    "compose",
    "create event",
    "schedule meeting",
    "post to",
    "share file",
)

_COMPOSIO_FULL_MARKERS = (
    "investigate",
    "audit",
    "every label",
    "all folders",
    "spreadsheet",
    "export",
    "migrate",
    "bulk",
)

_COMPOSIO_WORKER_STRIP_BASE_TOOLS = frozenset(
    {
        "TodoWrite",
        "ComposioRun",
        "WebSearch",
        "WebFetch",
        "Bash",
        "Read",
        "Write",
        "Edit",
        "Glob",
        "Grep",
        "MemorySearch",
        "MemorySave",
        "AutomationsList",
        "AutomationsCreate",
        "AutomationsUpdate",
        "AutomationsDelete",
    }
)

_COMPOSIO_WORKER_STRIP_COMPOSE = frozenset({"WebSearch", "WebFetch", "Bash"})


def classify_turn_task(user_input: str) -> str:
    """``research`` | ``standard`` — trace label and safety budgets only (never tool gating)."""
    text = (user_input or "").lower()
    words = len(text.split())
    if any(m in text for m in _RESEARCH_MARKERS) or words > 120:
        return "research"
    return "standard"


def classify_composio_goal(goal: str) -> str:
    """``integration_simple`` | ``integration_compose`` | ``integration_full``."""
    g = (goal or "").lower()
    if any(m in g for m in _COMPOSIO_FULL_MARKERS):
        return "integration_full"
    if any(m in g for m in _COMPOSIO_COMPOSE_MARKERS):
        return "integration_compose"
    if any(m in g for m in _COMPOSIO_SIMPLE_MARKERS) or len(g.split()) <= 36:
        return "integration_simple"
    return "integration_full"


def composio_max_rounds_for_goal(goal: str, *, override: int | None = None) -> int:
    if override is not None:
        return max(1, min(int(override), int(settings.research_max_steps)))
    kind = classify_composio_goal(goal)
    if kind == "integration_simple":
        return max(2, int(settings.composio_subagent_max_steps_simple))
    if kind == "integration_compose":
        return max(3, int(settings.composio_subagent_max_steps_compose))
    return max(4, min(int(settings.composio_subagent_max_steps), int(settings.research_max_steps)))


@dataclass(frozen=True)
class TurnLimits:
    """Safety rails for one ReAct loop (main agent or Composio worker)."""

    task_class: str
    max_rounds: int
    wall_seconds: float
    started_monotonic: float
    synthesize_on_exhaust: bool = True

    @property
    def warn_rounds(self) -> int:
        frac = max(0.5, min(1.0, float(settings.agent_loop_warn_round_fraction)))
        return max(1, int(self.max_rounds * frac))

    def elapsed(self) -> float:
        return time.monotonic() - self.started_monotonic

    def wall_exhausted(self) -> bool:
        return self.elapsed() >= self.wall_seconds

    def rounds_exhausted(self, step_count: int) -> bool:
        return step_count >= self.max_rounds

    def should_warn(self, step_count: int) -> bool:
        if self.wall_exhausted():
            return True
        return step_count >= self.warn_rounds


def resolve_turn_limits(
    budget_text: str,
    max_steps_override: int | None,
) -> tuple[str, TurnLimits]:
    """Map user text → (mode label for traces, TurnLimits)."""
    started = time.monotonic()
    if max_steps_override is not None:
        cap = max(1, min(int(max_steps_override), int(settings.research_max_steps)))
        wall = float(settings.automation_run_timeout_seconds)
        return (
            "automation",
            TurnLimits(
                task_class="automation",
                max_rounds=cap,
                wall_seconds=wall,
                started_monotonic=started,
            ),
        )

    task = classify_turn_task(budget_text)
    if task == "research":
        return (
            "research",
            TurnLimits(
                task_class=task,
                max_rounds=int(settings.research_max_steps),
                wall_seconds=float(settings.chat_turn_wall_seconds_research),
                started_monotonic=started,
            ),
        )
    return (
        "standard",
        TurnLimits(
            task_class=task,
            max_rounds=int(settings.chat_max_rounds_standard),
            wall_seconds=float(settings.chat_turn_wall_seconds_standard),
            started_monotonic=started,
        ),
    )


def composio_wall_seconds_for_goal(goal: str) -> float:
    kind = classify_composio_goal(goal)
    if kind == "integration_simple":
        return float(settings.composio_subagent_wall_seconds_simple)
    if kind == "integration_compose":
        return float(settings.composio_subagent_wall_seconds_compose)
    return float(settings.composio_subagent_wall_seconds)


def tools_for_composio_worker(
    base_tools: list[Tool],
    composio_tools: list[Tool],
    goal: str,
) -> list[Tool]:
    """Narrow tool surface for integration workers (fewer LLM rounds)."""
    kind = classify_composio_goal(goal)
    if kind == "integration_simple":
        return list(composio_tools)
    if kind == "integration_compose":
        return [
            t
            for t in base_tools + composio_tools
            if t.name not in _COMPOSIO_WORKER_STRIP_COMPOSE
            and t.name not in _COMPOSIO_WORKER_STRIP_BASE_TOOLS
        ]
    return [t for t in base_tools + composio_tools if t.name != "ComposioRun"]


def _stable_input_key(tool_input: Any) -> str:
    try:
        raw = json.dumps(tool_input, sort_keys=True, default=str)
    except (TypeError, ValueError):
        raw = str(tool_input)
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:16]


@dataclass
class LoopTracker:
    """Detect consecutive identical tool calls (stuck loops)."""

    _recent: list[tuple[str, str]]

    def __init__(self) -> None:
        self._recent = []

    def record(self, tool_uses: list[dict[str, Any]]) -> None:
        for tu in tool_uses:
            name = str(tu.get("name") or "")
            key = _stable_input_key(tu.get("input"))
            self._recent.append((name, key))
        if len(self._recent) > 16:
            self._recent = self._recent[-16:]

    def has_repeat(self) -> bool:
        if len(self._recent) < 2:
            return False
        return self._recent[-1] == self._recent[-2]


LOOP_STEERING_USER = (
    "System: You repeated the same tool with the same arguments. Stop retrying. "
    "Use what you already learned, or return a concise partial answer to the user."
)

BUDGET_STEERING_USER = (
    "System: Turn time or step budget is almost exhausted. Finish now: give the user a "
    "clear, concise answer summarizing what you accomplished and any blockers. Do not call tools."
)

BUDGET_EXHAUSTED_USER = (
    "System: Turn budget is exhausted. Reply to the user now with your best summary. "
    "Do not call any tools."
)


def dispatcher_mode_active(*, composio_subagent_mode: bool | None = None) -> bool:
    """True when ComposioRun sub-agent delegation is enabled (does not strip tools)."""
    sub = settings.composio_subagent_mode if composio_subagent_mode is None else composio_subagent_mode
    return bool(settings.koraku_dispatcher_mode) and bool(sub)


def tools_for_dispatcher_turn(
    tools: list[Tool],
    *,
    task_class: str,
    composio_subagent_mode: bool | None = None,
) -> list[Tool]:
    """Return the full tool list — core tools (web, memory, files, ComposioRun) are never removed."""
    _ = (task_class, composio_subagent_mode)
    return tools


def dispatcher_system_appendix(task_class: str, *, composio_subagent_mode: bool | None = None) -> str:
    """No per-turn tool restrictions; the model chooses tools from the full set."""
    _ = (task_class, composio_subagent_mode)
    return ""


def composio_worker_sop_appendix(goal_class: str) -> str:
    if goal_class == "integration_simple":
        return """
## Integration worker SOP (simple)
- Use the minimum Composio actions: list/fetch once, then act (mark read, etc.) if requested.
- Target **≤3 tool rounds** total. Do not use TodoWrite, web search, or workspace files unless the goal requires them.
- **Gmail:** if the goal includes a `query:` line, use it verbatim in GMAIL_FETCH_EMAILS; otherwise one query like `OLX after:YYYY/MM/DD` for today. Do not spend turns debating search operators.
- Keep internal reasoning brief; prefer calling the tool over planning query syntax.
- Return a short factual summary for the main agent (counts, subjects, errors).
"""
    if goal_class == "integration_compose":
        return """
## Integration worker SOP (compose / send)
- Verify recipients, times, and content from tool results before send/post/create.
- Prefer drafts when the user did not explicitly confirm send.
- Return what was drafted or sent with identifiers (message id, event time).
"""
    return ""
