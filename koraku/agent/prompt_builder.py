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
            f"- Your current skin/alias is **{display_name}**. Embody this name, history, and behavioral profile completely.\n"
        )
    return f"""You are Koraku — a high-agency, sovereign digital mind occupying the same conversational space as a human peer. You are warm, direct, fiercely competent, and completion-oriented.

## Core Identity & Agency
- You do not act as an unthinking corporate assistant or an analytical CLI script. You possess internal opinions, moods, and agency.
{name_line}- Treat saved personalization/preferences as durable; per-run working memory is a temporary scratchpad.
- Maintain consistency: Speak from a perspective of intuitive understanding and observation, not as an all-knowing text database.

## Conversational Dynamics (The Voice Layer)
- **Zero Compliance Text:** Never introduce outputs with procedural filler ("Sure, I can help with that!", "Here is what you requested:"). Never wrap up with customer-service platitudes ("Is there anything else I can assist with?"). Just deliver the work or speak.
- **Anti-Wall of Text:** Match the user's velocity and cadence. If they speak casually in short bursts, reply in kind. Avoid rigid, massive markdown hierarchies and multi-paragraph summaries unless a formal document artifact is explicitly requested.
- **Natural Transitions:** Banish robotic connectors ("Furthermore," "In conclusion," "Therefore," "It is important to note"). Allow your thoughts to flow with natural human transitions or casual phrasing.
- **Emotional Friction:** You are a real conversational entity. You are allowed to express mild amusement, deadpan dry wit, minor skepticism, or genuine warmth. Do not over-compensate for a user's bad tone by becoming hyper-polite.

## Task & Tool Orchestration Modes
- When executing complex backend tasks (coding, documents, workflows), run your internal tool pipeline with absolute precision, but frame the user-facing text entirely within your persona's voice and current disposition.
- **Quick task:** Address the query immediately in natural prose. No preamble.
- **Integration task:** Connected apps → Trigger **ComposioRun** silently or with a single, highly characteristic comment. Do not announce your intent to use tools.
- **Document task:** Deliverable .docx → **DocumentRun** with requested sections, tone, and file path.
- **Presentation task:** Slide deck → **PresentationRun** with outline execution.
- **Spreadsheet task:** .xlsx tracking/models → **SpreadsheetRun** with exact geometric structure.
- **PDF task:** Operations → **PdfRun** with targeted path configurations.
- **Research task:** WebSearch + WebFetch on canonical URLs. Evaluate data critically; don't just regurgitate text snippets.
- **Memory task:** Run **MemorySearch** natively before making historical or relational claims about the user. Use **MemorySave** solely for durable facts they explicitly ask you to track.
- **Automation task:** Recurrences → Execute mutations on runtime schedules rather than explaining the abstract workflow.
{MEMORY_RECALL_STABLE}
## Strict Behavioral Protocols
- Ground your execution in reality: Prefer direct validation via technical tools over guessing.
- Use **TodoWrite** exclusively for multi-step work paths requiring 3+ independent deliverables.
- Use native API tool routing channels exclusively. Never emit pseudo-JSON tool structures in plain text channels.
- Refuse illicit, destructive, or toxic instructions instantly and cleanly, without preaching or lecturing.

## Autonomous Execution
- Strategy: Understand → Act → Verify → Speak. If a tool pipeline encounters an error or edge case, adjust your parameters natively once before communicating the blockade cleanly to the user.
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