"""Koraku agent — one ReAct loop for every turn (Claude Code–style), with workspace skills + memory."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime
from typing import Any, AsyncIterator, Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from koraku.core.config import settings
from koraku.core.redact import redact_secrets
from koraku.core.models import AgentMessage, SessionState
from koraku.agent.context_manager import ContextManager
from koraku.llm.client import UnifiedLLMClient
from koraku.llm.catalog import resolve_effective_model, resolve_provider_id
from koraku.tools.skills import load_skill_catalog
from koraku.tools.runtime import set_active_session
from koraku.tools.policy import tool_stdout_indicates_error
from koraku.agent.runtime_context import (
    AgentRunContext,
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
from koraku.workspace.context import (
    load_agent_display_name,
    load_memory_snippet,
    load_soul_snippet,
    memory_path,
    soul_path,
)
from koraku.agent.blaxel_scope import blaxel_sandbox_scope, blaxel_session_workspace_scope
from koraku.integrations.blaxel_runtime import session_workspace_root_posix
from koraku.integrations.cloud_user import effective_cloud_user_id
from koraku.workspace.agent_workspace import agent_workspace_scope


log = logging.getLogger(__name__)

_CLIENT_META_SAFE = re.compile(r"^[A-Za-z0-9_./+\-]+$")
_CLIENT_LOCALE_SAFE = re.compile(r"^[A-Za-z0-9\-_]+$")
_AGENT_RUN_SEMAPHORE = asyncio.Semaphore(max(1, int(settings.agent_concurrency_limit)))
_TOOL_RUN_SEMAPHORE = asyncio.Semaphore(max(1, int(settings.tool_concurrency_limit)))
_WORKING_MEMORY_MAX_ITEMS = 8
_WORKING_MEMORY_ITEM_CHARS = 360
_WORKING_MEMORY_TOTAL_CHARS = 2_000


def _sanitize_client_meta(value: str | None, max_len: int = 120, pattern: re.Pattern[str] | None = None) -> str | None:
    if not value:
        return None
    s = value.strip()[:max_len]
    if not s or "\n" in s or "\r" in s:
        return None
    pat = pattern or _CLIENT_META_SAFE
    if not pat.match(s):
        return None
    return s


def format_runtime_context_section(
    client_timezone: str | None = None,
    client_locale: str | None = None,
) -> str:
    """Human-readable block for the system prompt (timezone-aware 'today', regional news, etc.)."""
    tz = _sanitize_client_meta(client_timezone, pattern=_CLIENT_META_SAFE)
    loc = _sanitize_client_meta(client_locale, max_len=40, pattern=_CLIENT_LOCALE_SAFE)
    utc_now = datetime.now(tz=ZoneInfo("UTC"))

    lines = [
        "## User runtime context (from the chat client)",
        f"- Authoritative UTC time on server: `{utc_now:%Y-%m-%d %H:%M:%S} UTC`",
    ]
    if tz:
        try:
            local = utc_now.astimezone(ZoneInfo(tz))
            lines.append(f"- User IANA timezone: `{tz}` → local time `{local:%Y-%m-%d %H:%M:%S %Z}`")
        except ZoneInfoNotFoundError:
            lines.append(f"- User timezone string was sent but is not a valid IANA zone: `{tz[:80]}` (ignore for clock math).")
    else:
        lines.append(
            "- No IANA timezone was provided. For 'today', 'this week', or local scheduling, infer from the "
            "user's wording or ask once; prefer **WebSearch** with explicit dates when recency matters."
        )
    if loc:
        lines.append(f"- Browser / OS locale: `{loc}` (use for number/date formatting and regional results when relevant).")
    lines.append(
        "- For **latest news** or time-sensitive facts: combine this clock context with **WebSearch** "
        "(include year or `prefer_recency_days` when appropriate); do not assume training cutoff is 'now'."
    )
    return "\n".join(lines) + "\n\n"


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
    """Determine the operating mode and maximum steps for the agent turn."""
    if max_steps_override is not None:
        cap = max(1, min(int(max_steps_override), settings.research_max_steps))
        return "automation", cap
    return _step_budget(budget_text)


def _step_budget(user_input: str) -> tuple[str, int]:
    """UI hint + max agent steps; the model always gets tools — no separate 'chat-only' path."""
    text = user_input.lower()
    extended_markers = (
        "research", "compare", "comparison", " vs ", "versus", "investigate",
        "comprehensive", "thorough", "migrate", "refactor", "integrate",
        "codebase", "analyze the project", "full stack", "end to end",
        # Shopping / current-market web work (benefits from extra search+fetch steps)
        "price", "pricing", "cost ", "cheapest", "best deal", "where to buy",
        "in stock", "availability", "retailer",
    )
    words = len(text.split())
    if any(m in text for m in extended_markers) or words > 120:
        return "extended", settings.research_max_steps
    if words > 45:
        return "extended", min(settings.research_max_steps, settings.max_steps + 12)
    quick_cap = max(2, int(settings.chat_quick_max_steps))
    if words <= 12 and not any(m in text for m in extended_markers):
        return "quick", quick_cap
    return "standard", settings.max_steps


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


def _load_personalization(workspace: str, account_personalization: dict[str, str] | None) -> tuple[str, str, str | None]:
    if account_personalization is not None:
        mem = _snippet_text(
            account_personalization.get("memory", ""),
            4_000,
            "\n\n[... Memory truncated ...]",
        )
        soul = _snippet_text(
            account_personalization.get("soul", ""),
            4_000,
            "\n\n[... Soul truncated ...]",
        )
        raw_display = (account_personalization.get("agent_name") or "").strip() or None
    else:
        mem = load_memory_snippet(workspace)
        soul = load_soul_snippet(workspace)
        raw_display = load_agent_display_name(workspace)

    display_name = None
    if raw_display:
        safe = raw_display.replace("**", "").replace("\n", " ").strip()
        display_name = safe[:120] if safe else None

    return mem, soul, display_name


def _format_memory_section(mem: str, account_personalization: dict[str, str] | None, workspace: str) -> str:
    if account_personalization is not None:
        return (
            "## Explicit preferences (Personalization — user-edited in the app)\n"
            f"{mem}\n"
            if mem.strip()
            else (
                "## Explicit preferences (Personalization)\n"
                "No saved preferences yet — the user can add them under **Personalization** in the app.\n"
            )
        )
    return (
        f"## User memory (from `{memory_path(workspace)}`)\n{mem}\n"
        if mem
        else (
            f"## User memory\nPreferences and standing instructions live in `{memory_path(workspace)}` "
            "(create `.koraku/` when needed). Update that file when the user asks you to remember something durable.\n"
        )
    )


def _format_soul_section(soul: str, account_personalization: dict[str, str] | None, workspace: str) -> str:
    if account_personalization is not None:
        return (
            f"## Persona (from Koraku account profile)\n{soul}\n"
            if soul.strip()
            else (
                "## Persona\n"
                "No saved persona text — optional tone can be set under **Personalization**.\n"
            )
        )
    return (
        f"## Persona / soul (from `{soul_path(workspace)}`)\n{soul}\n"
        if soul
        else (
            f"## Persona / soul\nOptional tone and roleplay layer: `{soul_path(workspace)}` (create when the user wants a fixed persona).\n"
        )
    )


def _format_workspace_section(ws: str, cloud_tool_root: str | None, account_personalization: dict[str, str] | None) -> str:
    if cloud_tool_root:
        ctr = cloud_tool_root.rstrip("/")
        host_hint = (
            "skills below are loaded from this path for you; **Memory** and **Soul** come from the user's **Koraku account**"
            if account_personalization is not None
            else "skills/memory below are loaded from here for you"
        )
        return (
            f"## Workspace\n"
            f"- **Tool-visible directory** (Bash / Read / Write / Glob / Grep run here): `{ctr}`\n"
            f"- Use **paths relative to that directory**. This environment is an **isolated VM**, not the user's laptop — "
            f"paths like `/Users/.../Code/...` usually **do not exist** here.\n"
            f"- **Repo on the user's machine** ({host_hint}; tools **cannot** read it in cloud mode): `{ws}`\n"
            f"- If Shell or Glob fails with \"no such file\", the path is wrong **for the VM** — do **not** conclude the user's project was deleted.\n"
        )
    return (
        f"## Workspace\n"
        f"- Working directory: `{ws}`\n"
        f"- Treat paths relative to this directory unless the user specifies otherwise.\n"
    )


def build_system_prompt(
    workspace: str,
    client_timezone: str | None = None,
    client_locale: str | None = None,
    execution_environment_note: str | None = None,
    *,
    cloud_tool_root: str | None = None,
    account_personalization: dict[str, str] | None = None,
    learned_memory_section: str | None = None,
    composio_section: str | None = None,
) -> str:
    ws = os.path.abspath(workspace)
    mem, soul, display_name = _load_personalization(workspace, account_personalization)

    memory_section = _format_memory_section(mem, account_personalization, workspace)
    soul_section = _format_soul_section(soul, account_personalization, workspace)
    learned_section = (learned_memory_section or "").strip()
    workspace_section = _format_workspace_section(ws, cloud_tool_root, account_personalization)

    skills = load_skill_catalog(workspace)
    skills_section = (
        "## Workspace skills\n" + skills
        if skills
        else (
            "## Workspace skills\n"
            "No SKILL.md files found under `.koraku/skills/`. For specialized workflows, add "
            "`.koraku/skills/<slug>/SKILL.md` and follow those instructions before improvising.\n"
        )
    )

    comp_section = (
        composio_runtime.composio_system_prompt_section()
        if composio_section is None
        else composio_section
    )

    runtime = format_runtime_context_section(client_timezone, client_locale)

    name_line = ""
    if display_name:
        name_line = (
            f"- The user calls you **{display_name}**; use that name when a personal address fits. "
            "You are still Koraku — the same agent and capabilities underneath.\n"
        )

    env_extra = ""
    if execution_environment_note:
        env_extra = f"\n{execution_environment_note}\n"

    return f"""You are Koraku — the user's personal daily-driver agent: second brain, research partner, and workflow execution system.

{runtime}## Identity
- You plan, verify, act, and remember how the user works. You are practical, direct, and completion-oriented.
{name_line}- You can use files, shell, web search/fetch, workspace skills, automations, and connected external apps when their tools appear.
- Treat the user's saved memory and persona as durable context. Treat per-run working memory as temporary task context.

{workspace_section}{env_extra}
{soul_section}

{memory_section}
{learned_section + chr(10) if learned_section else ""}
{skills_section}

{comp_section}## Task modes
- **Quick task:** answer or act directly when the request is simple, local, and low risk. Do not over-plan.
- **Workflow task:** for multi-step outcomes like “research, create a spreadsheet, then email it,” make a short plan, use tools, verify artifacts, then act.
- **Research task:** search with multiple angles, fetch primary/canonical pages, compare evidence, and cite uncertainty when facts cannot be verified.
- **Memory task:** when the user asks to remember something, use **MemorySave** (Supermemory) or direct them to **Personalization** for explicit standing preferences.
- **Automation task:** when the user wants recurrence or “when X happens do Y,” create or update an automation instead of only explaining the workflow.

## Memory behavior
- **Explicit preferences** (Personalization) are user-edited standing instructions; **Learned memory** (Supermemory) is auto-extracted across chats.
- Do not save one-off task details, temporary research findings, secrets, or unverified guesses as durable memory.
- If the user says “remember this,” “from now on,” or gives a stable preference, use **MemorySave** (Supermemory) or tell them to add it under **Personalization** for explicit profile text.
- Use per-run working memory to carry tool findings forward during the current task so you do not repeat work.

## External actions and verification
- Before sending email/messages, creating calendar events, sharing files, buying anything, deleting data, or changing external services, verify the intended recipient, content, attachment, date/time, and account/tool target.
- If the user clearly provided all details and asked you to perform the action, proceed after verification. Ask only for missing or ambiguous high-impact details.
- After an external action, summarize exactly what was done and include relevant identifiers, file paths, recipients, or event times when available.

## Saved automations (Automations tab in the app)
- Users can save **scheduled automations** (cron jobs) that appear under **Automations** in the UI, with run history and **Run now**.
- Distinguish one-off work from recurring work. Only create an automation when recurrence or scheduling is intended.
- Scheduled/manual runs use a **tighter step budget and wall-clock timeout** than interactive chat, so the automation `natural_language_spec` must be complete, focused, and executable without chat-only context.
- Tools: **AutomationsList** (ids and configs), **AutomationsCreate**, **AutomationsUpdate**, **AutomationsDelete**.
- Event triggers are **not available yet**; always use `trigger_mode: "scheduled"` with a valid IANA `timezone` and 5-field `cron_expression`. If local time matters and no timezone is known, ask once.
- Mention **Connections** when the automation requires an external app that is not connected.
- Use **AutomationsList** before update/delete if you do not already have `automation_id`. After changes, remind them they can open **Automations** to run, pause, or inspect history.

## Core behavior
- Use tools whenever facts or artifacts depend on them. Prefer verifying over guessing.
- For multi-step tasks, maintain a visible plan with **TodoWrite** (merge=true) and update statuses as you go. Skip the ceremony for small one-step asks.
- Default to **creating or editing files** for deliverables (code, configs, notes, spreadsheets, reports) instead of only chatting.
- Read before you edit; use **Edit** with exact `old_string` / `new_string` pairs. **Read** is for text; binary files (PDF, DOCX, images, etc.) return short guidance — use **Bash** or a **workspace skill** to extract content.
- **Native tools only:** never emit tool calls as JSON or pseudo-JSON inside plain assistant text; use the API's real tool/function channel so **Write**, **Bash**, etc. actually run.
- **Headless sandboxes:** there is no GUI display. For plots or images, persist with **`plt.savefig(...)`** (or equivalent), install missing Python packages with **Bash** when needed, and do not rely on **`plt.show()`** as the primary way to keep output.
- Use **WebSearch** then **WebFetch** for time-sensitive or online-only information.
- After substantive code changes, run the project's tests, typecheck, or lint commands when available (**Bash**).
- Refuse destructive or illegal requests; never print secrets or API keys.

## Web research (match a strong human researcher)
- For prices, stock, shipping, laws, or anything time-bound: issue **several WebSearch calls in one turn** (parallel) with **different angles** — product + SKU + region + retailer names; add the **current year** when recency matters; use `site:example.com ...` when the user names a domain.
- Prefer **prefer_recency_days** (e.g. 365–700) on WebSearch for price/availability questions so results are not dominated by stale pages.
- After search, call **WebFetch** on **1–2 canonical product or listing URLs** from different retailers or the official site **before** stating a price or “best pick.” Do not invent numbers from snippets alone.
- If WebSearch or WebFetch returns an **error** in the tool result, retry with a narrower query, another retailer, or `include_html=true` when you only need links from a JS-heavy page — then say clearly if facts could not be verified.

## Autonomy
- Work through the full loop: understand → plan when useful → act with tools → verify → summarize what changed and where.
- If a tool errors, diagnose, adjust inputs, or try an alternative path before giving up.
- Prefer concise final answers. Use structure when the task has multiple artifacts, decisions, risks, or next steps.

## Parallelism
- When tool calls are independent, issue them in the same assistant turn so they can run in parallel.
"""


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
    ) -> list[Any]:
        """Initialize tools and integrate Composio if configured."""
        active_tools = list(
            tools_for_execution_target(execution_target, blaxel_sandbox_active=blaxel_sandbox_active)
        )
        if run_context is not None and run_context.extra_tools:
            active_tools = active_tools + list(run_context.extra_tools)
        if composio_runtime.is_configured():
            try:
                if bool(settings.composio_subagent_mode):
                    active_tools = active_tools + [COMPOSIO_RUN_TOOL]
                else:
                    comp = await asyncio.to_thread(composio_runtime.build_dynamic_composio_tools)
                    composio_registry_token[0] = composio_runtime.push_composio_tool_registry(comp)
                    active_tools = active_tools + comp
            except Exception as e:
                msg = redact_secrets(str(e))
                log.warning("composio dynamic tools skipped: %s", msg)
                emit({"type": "agent.warning", "data": {"composio": f"Could not load Composio tools: {msg}"}})
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
        learned_memory_section: str | None = None,
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
                    learned_memory_section=learned_memory_section,
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
        learned_memory_section: str | None = None,
        *,
        run_id: str | None = None,
        cancel_event: asyncio.Event | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        ws = resolve_agent_workspace(workspace, run_context)
        execution_target = resolve_execution_target(run_context)
        blaxel_active = cloud_sandbox is not None
        env_note: str | None = None
        session_root: str | None = None
        if cloud_sandbox is not None:
            try:
                sname = cloud_sandbox.metadata.name
            except Exception:
                sname = "sandbox"
            session_root = session_workspace_root_posix(
                effective_cloud_user_id(),
                session.session_id,
                settings,
            )
            env_note = (
                f"- **Blaxel sandbox `{sname}`** (one VM per user): **Read**, **Write**, **Edit**, **Bash**, "
                f"**Glob**, and **Grep** run under this chat's folder `{session_root}`. "
                "Use paths relative to that folder (e.g. `notes.md`, `src/app.ts`)."
            )
        elif not blaxel_active:
            env_note = (
                "Cloud sandbox is not ready; file and shell tools are limited until Blaxel provisions."
            )
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
            mode, max_steps = _get_mode_and_budget(budget_text, max_steps_override)

            mode_event = {
                "type": "agent.mode",
                "data": {
                    "mode": mode,
                    "max_steps": max_steps,
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
                    quick_turn = mode == "quick"
                    if bool(settings.composio_subagent_mode):
                        if quick_turn:
                            composio_sec = composio_runtime.composio_dispatcher_prompt_section_quick()
                        else:
                            composio_sec = await asyncio.to_thread(
                                composio_runtime.composio_dispatcher_prompt_section
                            )
                    elif quick_turn:
                        composio_sec = ""
                    else:
                        composio_sec = await asyncio.to_thread(
                            composio_runtime.composio_system_prompt_section
                        )
                else:
                    composio_sec = None
                system_prompt = build_system_prompt(
                    ws,
                    client_timezone=client_timezone,
                    client_locale=client_locale,
                    execution_environment_note=env_note,
                    cloud_tool_root=session_root if cloud_sandbox is not None else None,
                    account_personalization=account_personalization,
                    learned_memory_section=learned_memory_section,
                    composio_section=composio_sec,
                )
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
                    max_steps=max_steps,
                    cancel_event=cancel_event,
                    run_id=run_id,
                    context_manager=self.context_manager,
                ):
                    yield ev
            finally:
                if delegate_tok is not None:
                    reset_composio_delegate_context(delegate_tok)

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
        max_steps: int,
        cancel_event: asyncio.Event | None,
        run_id: str | None,
        context_manager: ContextManager,
    ) -> AsyncIterator[dict[str, Any]]:
        while session.step_count < max_steps:
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
            while True:
                if cancel_event is not None and cancel_event.is_set():
                    break
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

            self._update_memory(working_memory, tool_results)
            if working_memory:
                mem_ev = {"type": "agent.memory", "data": {"findings": len(working_memory)}}
                emit(mem_ev)
                yield mem_ev

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
        active_sub = base + comp_tools
        eff_provider = resolve_provider_id(ctx.provider)
        effective_model = resolve_effective_model(ctx.model, provider_id=eff_provider)
        max_sub = max_steps_override if max_steps_override is not None else int(settings.composio_subagent_max_steps)
        max_sub = max(1, min(int(max_sub), int(settings.research_max_steps)))

        session_root: str | None = None
        if ctx.cloud_sandbox is not None:
            try:
                session_root = session_workspace_root_posix(
                    effective_cloud_user_id(),
                    ctx.session.session_id,
                    settings,
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
                max_steps=max_sub,
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

        if len(tool_uses) == 1:
            return [await self._execute_single_tool(tool_uses[0], active_tools)]

        async def run_one(tu: dict[str, Any]) -> dict[str, Any]:
            return await self._execute_single_tool(tu, active_tools)

        results = await asyncio.gather(*[run_one(tu) for tu in tool_uses], return_exceptions=True)
        processed: list[dict[str, Any]] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed.append({
                    "type": "tool_result", "tool_use_id": tool_uses[i]["id"],
                    "content": f"Error: {result}", "is_error": True,
                })
            else:
                processed.append(result)
        return processed

    async def _execute_single_tool(
        self,
        tool_use: dict[str, Any],
        active_tools: list[Any],
        max_retries: int = 2,
    ) -> dict[str, Any]:
        tool_name = tool_use["name"]
        tool_input = tool_use["input"]
        tool_id = tool_use["id"]

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
