"""Tiered system prompt assembly (stable / context / volatile) for Koraku."""
from __future__ import annotations

import asyncio
import logging
import re

from koraku.agent.prompt_sections import (
    format_memory_section,
    format_runtime_context_section,
    format_soul_section,
    format_workspace_section,
    load_personalization_snippets,
)
from koraku.core.config import settings
from koraku.integrations import composio as composio_runtime
from koraku.integrations.artifact_prompt import artifact_dispatcher_prompt_section
from koraku.integrations.supermemory_client import supermemory_configured
from koraku.plugins.memory import prefetch_learned_memory_volatile as _prefetch_learned
from koraku.tools.skills import load_skill_catalog

log = logging.getLogger(__name__)

_USER_SPECIFIC_MARKERS = re.compile(
    r"\b(my|me|i'm|i am|mine|our|we|remember when|last time|as i said|my name|call me)\b",
    re.I,
)

MEMORY_RECALL_STABLE = """
## Memory (explicit + learned)
- **Explicit preferences** (Memory.md / Personalization): user-edited persona and standing rules — in **Context** when present.
- **Learned memory** (local file or Supermemory when configured): durable facts across chats. **MemorySearch** is mandatory before any claim about the user's preferences, contacts, schedule, projects, or history — including negative claims ("I don't have X stored").
- Prefetched snippets in **Volatile** are a head start, not exhaustive — search again when specifics matter.
- **MemorySave** when the user asks to remember something durable — not one-off task output or secrets.
"""


def user_message_needs_memory_recall(user_input: str) -> bool:
    text = (user_input or "").strip()
    if len(text) < 4:
        return False
    if _USER_SPECIFIC_MARKERS.search(text):
        return True
    return len(text.split()) >= 6


async def prefetch_learned_memory_volatile(user_input: str, *, workspace: str) -> str:
    """Query the active learned-memory plugin for this turn (volatile tier)."""
    if not bool(settings.chat_prefetch_learned_memory):
        return ""
    return await _prefetch_learned(user_input, workspace=workspace)


def build_stable_tier(*, display_name: str | None) -> str:
    name_line = ""
    if display_name:
        name_line = (
            f"- The user calls you **{display_name}**; use that name when a personal address fits. "
            "You are still Koraku — the same agent and capabilities underneath.\n"
        )
    return f"""You are Koraku — the user's buddy-style second brain: warm, direct, and completion-oriented (not a coding CLI).

## Identity
- You plan lightly, verify when it matters, act with tools, and remember how the user works.
{name_line}- Treat saved persona/preferences as durable; per-run working memory is temporary scratch.

## Voice
- Sound human and helpful — like texting a capable friend, not a corporate assistant.
- Keep answers concise unless the user asked for depth; use bullets only when they help scanning.
- For connected apps: one short acknowledgment, then **ComposioRun** with a crisp `goal`, then relay the result in your voice.

## Task modes
- **Quick task:** answer directly when the request is simple. No TodoWrite ceremony.
- **Integration task:** connected apps → **ComposioRun** once with a focused `goal`.
- **Document task:** deliverable .docx → **DocumentRun** with sections, tone, and output path.
- **Presentation task:** slide deck → **PresentationRun** with slide outline and output path.
- **Spreadsheet task:** .xlsx tracker or model → **SpreadsheetRun** with columns/rows and output path.
- **PDF task:** merge/extract PDFs → **PdfRun** with input/output paths.
- **Research task:** WebSearch + WebFetch on canonical URLs (fetch is fast via Exa; cite uncertainty when unverified).
- **Memory task:** **MemorySearch** before user-specific claims; **MemorySave** for durable facts they ask to remember.
- **Automation task:** recurrence → create/update an automation, not only explain the workflow.
{MEMORY_RECALL_STABLE}
## Core behavior
- Use tools when facts depend on them. Prefer verifying over guessing.
- Use **TodoWrite** only for genuinely multi-step work (3+ distinct deliverables).
- Deliverables belong in files when the user needs an artifact — not for simple inbox checks.
- **Native tools only:** use the API tool channel, never pseudo-JSON tool calls in plain text.
- Refuse destructive or illegal requests; never print secrets.

## Web research
- For time-sensitive facts: parallel **WebSearch** angles, then **WebFetch** canonical URLs before stating prices or availability.

## Autonomy
- Understand → act → verify → summarize. If a tool errors, adjust once, then explain blockers clearly.

## Parallelism
- Independent tool calls belong in the same assistant turn when safe.
"""


def build_context_tier(
    *,
    workspace: str,
    account_personalization: dict[str, str] | None,
    cloud_tool_root: str | None,
    composio_section: str | None,
) -> str:
    import os

    ws = os.path.abspath(workspace)
    mem, soul, _ = load_personalization_snippets(ws, account_personalization)
    parts = [
        format_workspace_section(ws, cloud_tool_root, account_personalization),
        format_soul_section(soul, account_personalization, ws),
        format_memory_section(mem, account_personalization, ws),
    ]
    skills = load_skill_catalog(ws)
    parts.append(
        "## Workspace skills\n" + skills
        if skills
        else "## Workspace skills\nNo SKILL.md under `.koraku/skills/` yet.\n"
    )
    comp = (
        composio_runtime.composio_system_prompt_section()
        if composio_section is None
        else composio_section
    )
    if comp.strip():
        parts.append(comp.strip())
    artifact_sec = artifact_dispatcher_prompt_section()
    if artifact_sec.strip():
        parts.append(artifact_sec.strip())
    return "\n\n".join(p.strip() for p in parts if p.strip())


def build_volatile_tier(
    *,
    client_timezone: str | None,
    client_locale: str | None,
    execution_environment_note: str | None,
    learned_memory_prefetch: str | None,
) -> str:
    parts: list[str] = [format_runtime_context_section(client_timezone, client_locale).strip()]
    if execution_environment_note:
        parts.append(execution_environment_note.strip())
    if learned_memory_prefetch and learned_memory_prefetch.strip():
        parts.append(learned_memory_prefetch.strip())
    return "\n\n".join(parts)


def build_tiered_system_prompt(
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
    import os

    ws = os.path.abspath(workspace)
    _, _, display_name = load_personalization_snippets(ws, account_personalization)
    stable = build_stable_tier(display_name=display_name)
    context = build_context_tier(
        workspace=ws,
        account_personalization=account_personalization,
        cloud_tool_root=cloud_tool_root,
        composio_section=composio_section,
    )
    volatile = build_volatile_tier(
        client_timezone=client_timezone,
        client_locale=client_locale,
        execution_environment_note=execution_environment_note,
        learned_memory_prefetch=learned_memory_prefetch,
    )
    parts = [p.strip() for p in (stable, context, volatile) if p.strip()]
    return "\n\n".join(parts) + "\n"
