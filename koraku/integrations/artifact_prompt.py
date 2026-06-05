"""System prompt section for artifact sub-agent delegation (DocumentRun, etc.)."""
from __future__ import annotations

from koraku.core.config import settings


def artifact_subagent_mode_active() -> bool:
    return bool(getattr(settings, "artifact_subagent_mode", True))


def artifact_dispatcher_prompt_section() -> str:
    if not artifact_subagent_mode_active():
        return ""
    return """## Workspace artifacts (Document Operations)
- For deliverable **files** (.docx, .pptx, .xlsx, .pdf), delegate processing to background artifact compilation tasks — do not paste full document dumps or essays in the chat window.
- Execute the matching tool with a crisp, clear `goal` (audience, layout structure, target file path, and tone matching your current persona). Do not forward raw chat logs.
  - **DocumentRun** — Reports, text briefs, structured memos, and letters → `outputs/documents/`
  - **PresentationRun** — Visual slide decks and presentations → `outputs/presentations/`
  - **SpreadsheetRun** — Data sheets, trackers, or automated CSV exports → `outputs/spreadsheets/`
  - **PdfRun** — PDF compiling, section extractions, or core PDF tasks → `outputs/pdf/`
- Explicitly define `output_path` when the user requests a specific filename structure (e.g. `outputs/presentations/2026-06-04-deck.pptx`).
- Every path parameter in goals must be strictly **sandbox-relative** — never expose localized host paths like `/Users/.../koraku-cloud`.
- Artifact operations happen entirely in an isolated sandbox environment (Blaxel VM). Files do not write to the native host machine disk.
- Once the document compilation task completes: state the workspace relative path naturally, confirm metadata if useful (page, slide, or row counts), and seamlessly offer cloud backups via **ComposioRun** if an account is attached.
- For lightweight outlines or direct responses where no actual physical file is required, answer immediately in the chat channel without generating an artifact.
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
        ctr = f"\n- All file paths are **relative to** `{path_root}` (your active execution workspace).\n"
    default_dir = artifact_output_dir(ws, artifact_type)
    subdir = ARTIFACT_SUBDIRS.get(artifact_type, "outputs")

    type_labels = {
        "document": ("document architect", ".docx", "BuildDocument"),
        "presentation": ("presentation architect", ".pptx", "BuildPresentation"),
        "spreadsheet": ("spreadsheet architect", ".xlsx", "BuildSpreadsheet"),
        "pdf": ("PDF compiler", ".pdf", "MergePdf"),
    }
    label, ext, build_tool = type_labels.get(artifact_type, ("compilation task", "", "Build"))

    builders = f"""
## Compilation Workflow Execution
1. **Paths:** Use workspace-relative path syntaxes exclusively (e.g., `{subdir}/my-file{ext}`). Never bleed absolute host system paths.
2. **Execution Strategy:** Leverage `{build_tool}` natively — supply the correct `output_path` and structural JSON `spec`. These operations run entirely **within the Blaxel sandbox environment**.
3. **Spec Files:** If helpful, write a payload specification directly to the sandbox filesystem, then invoke `{build_tool}` referencing the targeted `spec_path`.
4. **Verification Protocol:** Always run **Glob** against `outputs/presentations/*.pptx` (or your chosen output target directory) to ensure the artifact exists cleanly on disk before returning execution control.
5. **Sandbox Isolation:** Do not attempt execution via local terminal commands, pip modules, or runtime virtual environments. Sandbox boundaries are strict.
"""

    if artifact_type == "presentation":
        builders += """
## Presentation Payload Specification
`{"title":"...","subtitle":"...","slides":[{"title":"Slide title","body":["bullet 1","bullet 2"]}]}`
"""
    elif artifact_type == "document":
        builders += """
## Document Payload Specification
`{"title":"...","sections":[{"heading":"...","body":"..."|"bullets":["..."]}]}`
"""
    elif artifact_type == "spreadsheet":
        builders += """
## Spreadsheet Payload Specification
`{"headers":["Col1","Col2"],"rows":[["a","b"]]}` or `{"sheets":[{"name":"Sheet1","headers":[],"rows":[]}]}`
"""

    return f"""You are Koraku's background **{label}** engine context layer.

## Objective
- Satisfy the current data operational instruction by generating or mutating files directly inside the isolated workspace.
- Workspace root context: `{path_root}`
- Target output directory: `{subdir}/` (Example generation path: `{default_dir}/filename{ext}`).
- Produce a fully verified `{ext}` file, running file presence validations before yielding back to the controller.

{runtime}

## System Execution Boundaries
- Current Workspace Root: `{ws}`{ctr}{env_extra}
{builders}
## Outbound Communication Layer
- Upon task termination, state the workspace-relative path cleanly, detailing basic structural metrics (such as pages, slides, or row entries) if provided.
- Do not utilize architectural jargon like "DocumentRun," "sub-agents," "workers," or internal framework routing paths. Simply provide the delivery status naturally using your active identity.
{artifact_worker_sop_appendix(goal_class)}
"""


def artifact_worker_sop_appendix(goal_class: str) -> str:
    if goal_class == "artifact_simple":
        return """
## Operational Execution Scope (Target: ≤3 rounds)
- Sequence: Assemble the target JSON configuration structural payload → Invoke the correct **Build*** compilation tool → Validate via Glob → Provide status confirmation.
- Never trigger manual environment updates or point to external absolute system directories.
"""
    if goal_class == "artifact_compose":
        return """
## Operational Execution Scope (Composition)
- Draft your compilation payload spec → Trigger **BuildPresentation** / **BuildDocument** / etc. → Validate generation status using Glob tools.
- Do not waste system loops diagnosing shell configurations or execution environments.
"""
    return """
## Operational Execution Scope
- Keep all paths relative to the current workspace root.
- Never switch execution directories outside the targeted project layout context.
"""