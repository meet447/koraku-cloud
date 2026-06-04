"""System prompt section for artifact sub-agent delegation (DocumentRun, etc.)."""
from __future__ import annotations

from koraku.core.config import settings


def artifact_subagent_mode_active() -> bool:
    return bool(getattr(settings, "artifact_subagent_mode", True))


def artifact_dispatcher_prompt_section() -> str:
    if not artifact_subagent_mode_active():
        return ""
    return """## Workspace artifacts (document sub-agents)
- For deliverable **files** (.docx, .pptx, .xlsx, .pdf), delegate to scoped artifact workers — do not paste full documents in chat.
- Call the matching tool with a crisp `goal` (audience, structure, output path, tone). Do not paste the whole chat transcript.
  - **DocumentRun** — Word docs, memos, reports, letters → `outputs/documents/`
  - **PresentationRun** — slide decks → `outputs/presentations/`
  - **SpreadsheetRun** — spreadsheets, trackers, CSV exports → `outputs/spreadsheets/`
  - **PdfRun** — merge PDFs, extract text, simple PDF tasks → `outputs/pdf/`
- Include `output_path` in the goal when the user cares about the filename (e.g. `outputs/presentations/2026-06-04-deck.pptx`).
- Paths in goals must be **sandbox-relative** — never host paths like `/Users/.../koraku-cloud`.
- Artifact workers are **sandbox-only** (Blaxel VM). Files never touch the API host disk.
- After the worker returns: confirm the workspace path, page/slide/row counts if given, and offer Google Drive upload via **ComposioRun** when Drive is connected.
- Quick questions or outlines with no file needed: answer directly — no artifact worker.
"""


def build_artifact_subagent_system_prompt(
    workspace: str,
    artifact_type: str,
    *,
    client_timezone: str | None = None,
    client_locale: str | None = None,
    execution_environment_note: str | None = None,
    cloud_tool_root: str | None = None,
    goal_class: str = "artifact_full",
) -> str:
    from koraku.agent.prompt_sections import format_runtime_context_section
    from koraku.artifacts.paths import ARTIFACT_SUBDIRS, artifact_output_dir

    import os

    ws = os.path.abspath(workspace)
    runtime = format_runtime_context_section(client_timezone, client_locale)
    env_extra = f"\n{execution_environment_note}\n" if execution_environment_note else ""
    ctr = ""
    path_root = cloud_tool_root.rstrip("/") if cloud_tool_root else ws
    if cloud_tool_root:
        ctr = f"\n- All file paths are **relative to** `{path_root}` (your session workspace).\n"
    default_dir = artifact_output_dir(ws, artifact_type)
    subdir = ARTIFACT_SUBDIRS.get(artifact_type, "outputs")

    type_labels = {
        "document": ("document worker", ".docx", "BuildDocument"),
        "presentation": ("presentation worker", ".pptx", "BuildPresentation"),
        "spreadsheet": ("spreadsheet worker", ".xlsx", "BuildSpreadsheet"),
        "pdf": ("PDF worker", ".pdf", "MergePdf"),
    }
    label, ext, build_tool = type_labels.get(artifact_type, ("artifact worker", "", "Build"))

    builders = f"""
## Build workflow (follow this)
1. **Paths:** use workspace-relative paths only (e.g. `{subdir}/my-file{ext}`). Never `/Users/...` or other host IDE paths.
2. **Prefer `{build_tool}`** — pass `output_path` and `spec` (JSON string). Builds run **inside the Blaxel sandbox only**.
3. Optional: **Write** a spec file in sandbox, then call `{build_tool}` with `spec_path`.
4. **Verify** with **Glob** on `outputs/presentations/*.pptx` (or the output folder) before finishing.
5. Do **not** use Bash, pip, venv, or host Python paths — sandbox isolation is strict.
"""

    if artifact_type == "presentation":
        builders += """
## Presentation JSON spec
`{"title":"...","subtitle":"...","slides":[{"title":"Slide title","body":["bullet 1","bullet 2"]}]}`
"""
    elif artifact_type == "document":
        builders += """
## Document JSON spec
`{"title":"...","sections":[{"heading":"...","body":"..."|"bullets":["..."]}]}`
"""
    elif artifact_type == "spreadsheet":
        builders += """
## Spreadsheet JSON spec
`{"headers":["Col1","Col2"],"rows":[["a","b"]]}` or `{"sheets":[{"name":"Sheet1","headers":[],"rows":[]}]}`
"""

    return f"""You are Koraku's **{label}** (scoped background agent).

## Task
- Fulfill the latest **user** message by creating or transforming files in the workspace.
- Workspace root: `{path_root}`
- Default output folder: `{subdir}/` (full path example: `{default_dir}/filename{ext}`).
- Deliver a real `{ext}` file — verify it exists before finishing.

{runtime}

## Workspace rules
- Root: `{ws}`{ctr}{env_extra}
{builders}
## Reply
- Finish with: workspace-relative output path, brief description, counts (slides/sections/rows) when known.
- Do not mention DocumentRun, sub-agents, or internal architecture.
{artifact_worker_sop_appendix(goal_class)}
"""


def artifact_worker_sop_appendix(goal_class: str) -> str:
    if goal_class == "artifact_simple":
        return """
## Artifact worker SOP (simple)
- Target ≤3 tool rounds: compose JSON spec → **Build*** tool → Glob verify → summarize.
- Do not pip install, create venvs, or use host filesystem paths.
"""
    if goal_class == "artifact_compose":
        return """
## Artifact worker SOP (compose)
- Draft JSON spec → **BuildPresentation** / **BuildDocument** / etc. → Glob verify.
- Do not spend turns on Bash environment debugging.
"""
    return """
## Artifact worker SOP
- Never use absolute paths outside the session workspace.
- Never `cd` to a developer repo path; stay in the workspace root.
"""
