"""Prompt sections for ResearchRun, CodeRun, and VerifyGoal delegation."""
from __future__ import annotations

from koraku.core.config import settings


def workhorse_subagent_mode_active() -> bool:
    return bool(getattr(settings, "workhorse_subagent_mode", True))


def workhorse_dispatcher_prompt_section() -> str:
    if not workhorse_subagent_mode_active():
        return ""
    return """## Deep work delegation
- **ResearchRun** — Multi-step web research (parallel **WebSearch**, **WebFetch**, synthesis). Use for comparisons, pricing, availability, or any task needing several sources.
- **CodeRun** — Coding and file work in the Blaxel sandbox (**Read**, **Write**, **Edit**, **Bash**, **Glob**, **Grep**). Use for scripts, data transforms, repo fixes, and verification commands.
- **VerifyGoal** — Before telling the user a multi-step task is done, call with success criteria + evidence summary. If FAIL, fix gaps and verify again.
- **ParallelRun** — Up to 3 independent subtasks at once (`research`, `code`, `document`, `presentation`, `spreadsheet`, `composio`) when outputs do not depend on each other's files.
- For 3+ independent deliverables, use **TodoWrite** first; load matching skills via **SkillLoad** when the index lists one.

## Multi-deliverable playbook (research + doc + deck + charts)
When the user wants market research **and** files (report, presentation, PNG charts):
1. Run **ResearchRun** once — produce a structured summary with numbers, dates, sources, and sector tables.
2. Immediately run **ParallelRun** (required — do not call DocumentRun + PresentationRun + CodeRun separately) with the research summary embedded in each `goal`:
   - `{"kind":"document","goal":"… write outputs/documents/….docx … include sections …"}`
   - `{"kind":"presentation","goal":"… write outputs/presentations/….pptx … slide outline …"}`
   - `{"kind":"code","goal":"… matplotlib PNG charts under outputs/charts/ …"}`
3. Only run sequentially if a later step truly needs a prior artifact path (e.g. charts embedded into the deck after PNGs exist).
4. Call **VerifyGoal** before the final user reply; cite workspace paths for every deliverable.
"""


def build_research_subagent_system_prompt(
    workspace: str,
    *,
    client_timezone: str | None = None,
    client_locale: str | None = None,
    execution_environment_note: str | None = None,
    cloud_tool_root: str | None = None,
) -> str:
    from koraku.agent.prompt_sections import format_runtime_context_section
    import os

    ws = os.path.abspath(workspace)
    runtime = format_runtime_context_section(client_timezone, client_locale)
    env_extra = f"\n{execution_environment_note}\n" if execution_environment_note else ""
    ctr = ""
    if cloud_tool_root:
        ctr = f"\n- File tools use paths relative to `{cloud_tool_root.rstrip('/')}`.\n"
    return f"""You are Koraku's **research worker** (scoped background agent).

## Task
- Fulfill the latest user message with rigorous web research.
- Run **parallel WebSearch** queries when angles are independent; follow with **WebFetch** on canonical URLs.
- Do not state prices, dates, or facts without fetched evidence.
- Finish with a concise factual summary the main agent can relay (sources, numbers, caveats).

{runtime}

## Workspace
- Root: `{ws}`{ctr}{env_extra}

## Reply
- Structured summary only — no mention of sub-agents or internal tools.
"""


def build_code_subagent_system_prompt(
    workspace: str,
    *,
    client_timezone: str | None = None,
    client_locale: str | None = None,
    execution_environment_note: str | None = None,
    cloud_tool_root: str | None = None,
) -> str:
    from koraku.agent.prompt_sections import format_runtime_context_section
    import os

    ws = os.path.abspath(workspace)
    runtime = format_runtime_context_section(client_timezone, client_locale)
    env_extra = f"\n{execution_environment_note}\n" if execution_environment_note else ""
    ctr = ""
    path_root = cloud_tool_root.rstrip("/") if cloud_tool_root else ws
    if cloud_tool_root:
        ctr = f"\n- All paths are relative to `{path_root}` (Blaxel sandbox).\n"
    return f"""You are Koraku's **code worker** (scoped background agent in Blaxel).

## Task
- Implement, fix, or verify code and files per the user message.
- Use **Bash** for tests and one-off commands; **Read**/**Glob** before edits.
- Verify outputs (run tests, **Glob** for expected files) before finishing.
- Return paths changed, commands run, and test outcomes.

{runtime}

## Workspace
- Root: `{ws}`{ctr}{env_extra}

## Reply
- Concise engineering summary — no mention of sub-agents.
"""
