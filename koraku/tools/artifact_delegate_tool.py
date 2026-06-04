"""Artifact delegate tools — DocumentRun, PresentationRun, SpreadsheetRun, PdfRun."""
from __future__ import annotations

from koraku.agent.composio_delegate_context import get_composio_delegate_context
from koraku.tools.tool_def import Tool

ARTIFACT_TOOL_NAMES: tuple[str, ...] = (
    "DocumentRun",
    "PresentationRun",
    "SpreadsheetRun",
    "PdfRun",
)

_ARTIFACT_TYPES: dict[str, str] = {
    "DocumentRun": "document",
    "PresentationRun": "presentation",
    "SpreadsheetRun": "spreadsheet",
    "PdfRun": "pdf",
}


async def _artifact_run_handler(
    goal: str,
    *,
    artifact_type: str,
    max_steps: int | None = None,
    output_path: str | None = None,
) -> str:
    ctx = get_composio_delegate_context()
    if ctx is None:
        return "Error: Artifact workers are only available during an active chat turn."
    agent = ctx.agent
    fn = getattr(agent, "_execute_artifact_subagent", None)
    if fn is None:
        return "Error: Artifact sub-agent execution is not wired (internal)."
    merged_goal = (goal or "").strip()
    if output_path and output_path.strip():
        merged_goal = f"{merged_goal}\n\nOutput path: {output_path.strip()}"
    return await fn(
        artifact_type=artifact_type,
        goal=merged_goal,
        max_steps_override=max_steps,
    )


def _make_artifact_tool(name: str, artifact_type: str, description: str) -> Tool:
    async def handler(goal: str, max_steps: int | None = None, output_path: str | None = None) -> str:
        return await _artifact_run_handler(
            goal,
            artifact_type=artifact_type,
            max_steps=max_steps,
            output_path=output_path,
        )

    return Tool(
        name=name,
        description=description,
        input_schema={
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": (
                        "Single-task instruction for the artifact worker: topic, audience, "
                        "structure/sections, tone, and output filename when known."
                    ),
                },
                "output_path": {
                    "type": "string",
                    "description": (
                        "Optional workspace-relative path for the deliverable "
                        "(e.g. outputs/documents/report.docx)."
                    ),
                },
                "max_steps": {
                    "type": "integer",
                    "description": "Optional max ReAct steps for this sub-run.",
                },
            },
            "required": ["goal"],
        },
        handler=handler,
        categories=["artifact", "delegate", artifact_type],
    )


DOCUMENT_RUN_TOOL = _make_artifact_tool(
    "DocumentRun",
    "document",
    (
        "Spawn a **document worker** to create .docx files (memos, reports, proposals, letters) "
        "in the workspace under outputs/documents/. Pass a clear goal with sections, tone, and output path."
    ),
)

PRESENTATION_RUN_TOOL = _make_artifact_tool(
    "PresentationRun",
    "presentation",
    (
        "Spawn a **presentation worker** to create .pptx slide decks in outputs/presentations/. "
        "Include slide titles, bullet content, slide count, and style notes in the goal."
    ),
)

SPREADSHEET_RUN_TOOL = _make_artifact_tool(
    "SpreadsheetRun",
    "spreadsheet",
    (
        "Spawn a **spreadsheet worker** to create .xlsx or structured CSV exports in outputs/spreadsheets/. "
        "Include columns, sample rows, formulas needed, and output path in the goal."
    ),
)

PDF_RUN_TOOL = _make_artifact_tool(
    "PdfRun",
    "pdf",
    (
        "Spawn a **PDF worker** for merge, split, or text extraction tasks in outputs/pdf/. "
        "Include input file paths and desired output path in the goal."
    ),
)

ARTIFACT_RUN_TOOLS: list[Tool] = [
    DOCUMENT_RUN_TOOL,
    PRESENTATION_RUN_TOOL,
    SPREADSHEET_RUN_TOOL,
    PDF_RUN_TOOL,
]
