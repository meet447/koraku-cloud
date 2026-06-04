"""In-process artifact builders — sandbox-only (Blaxel VM, no host filesystem)."""
from __future__ import annotations

import json
from typing import Any

from koraku.artifacts.sandbox_gate import read_json_spec_from_sandbox, require_sandbox_for_artifacts
from koraku.tools.tool_def import Tool


async def _load_spec(*, spec: str | None, spec_path: str | None) -> tuple[dict[str, Any] | None, str | None]:
    gate = await require_sandbox_for_artifacts()
    if gate:
        return None, gate

    if spec and str(spec).strip():
        try:
            parsed = json.loads(spec)
        except json.JSONDecodeError as e:
            return None, f"Error: invalid JSON in `spec`: {e}"
        if not isinstance(parsed, dict):
            return None, "Error: `spec` must be a JSON object."
        return parsed, None

    if spec_path and str(spec_path).strip():
        return await read_json_spec_from_sandbox(str(spec_path).strip())

    return None, "Error: provide `spec` (JSON string) or `spec_path` (workspace-relative file in sandbox)."


async def _build_document(
    output_path: str,
    spec: str | None = None,
    spec_path: str | None = None,
) -> str:
    from koraku.artifacts.blaxel_build import blaxel_build_artifact

    spec_dict, err = await _load_spec(spec=spec, spec_path=spec_path)
    if err:
        return err
    assert spec_dict is not None
    return await blaxel_build_artifact("document", spec_dict, output_path)


async def _build_presentation(
    output_path: str,
    spec: str | None = None,
    spec_path: str | None = None,
) -> str:
    from koraku.artifacts.blaxel_build import blaxel_build_artifact

    spec_dict, err = await _load_spec(spec=spec, spec_path=spec_path)
    if err:
        return err
    assert spec_dict is not None
    result = await blaxel_build_artifact("presentation", spec_dict, output_path)
    if result.startswith("Error"):
        return result
    try:
        payload = json.loads(result.strip().splitlines()[-1])
        slides = len(spec_dict.get("slides") or []) + (1 if spec_dict.get("title") else 0)
        payload.setdefault("slides", slides)
        return json.dumps(payload)
    except (json.JSONDecodeError, IndexError):
        return result


async def _build_spreadsheet(
    output_path: str,
    spec: str | None = None,
    spec_path: str | None = None,
) -> str:
    from koraku.artifacts.blaxel_build import blaxel_build_artifact

    spec_dict, err = await _load_spec(spec=spec, spec_path=spec_path)
    if err:
        return err
    assert spec_dict is not None
    return await blaxel_build_artifact("spreadsheet", spec_dict, output_path)


async def _merge_pdf(output_path: str, inputs: list[str]) -> str:
    from koraku.artifacts.blaxel_build import blaxel_merge_pdfs

    gate = await require_sandbox_for_artifacts()
    if gate:
        return gate
    if not inputs:
        return "Error: `inputs` must list at least one PDF path."
    return await blaxel_merge_pdfs(inputs, output_path)


_SPEC_SCHEMA = {
    "type": "object",
    "properties": {
        "output_path": {
            "type": "string",
            "description": "Sandbox-relative output path (e.g. outputs/presentations/deck.pptx).",
        },
        "spec": {
            "type": "string",
            "description": "JSON object string with slide/section content (preferred).",
        },
        "spec_path": {
            "type": "string",
            "description": "Sandbox-relative path to a JSON spec file (written with Write in sandbox).",
        },
    },
    "required": ["output_path"],
}


BUILD_DOCUMENT_TOOL = Tool(
    name="BuildDocument",
    description=(
        "Build a .docx file in the Blaxel sandbox from a JSON spec. "
        "Sandbox-only — files never touch the API host disk."
    ),
    input_schema=_SPEC_SCHEMA,
    handler=_build_document,
    categories=["artifact", "document"],
)

BUILD_PRESENTATION_TOOL = Tool(
    name="BuildPresentation",
    description=(
        "Build a .pptx slide deck in the Blaxel sandbox from a JSON spec. "
        "Sandbox-only — files never touch the API host disk."
    ),
    input_schema=_SPEC_SCHEMA,
    handler=_build_presentation,
    categories=["artifact", "presentation"],
)

BUILD_SPREADSHEET_TOOL = Tool(
    name="BuildSpreadsheet",
    description=(
        "Build an .xlsx spreadsheet in the Blaxel sandbox from a JSON spec. "
        "Sandbox-only — files never touch the API host disk."
    ),
    input_schema=_SPEC_SCHEMA,
    handler=_build_spreadsheet,
    categories=["artifact", "spreadsheet"],
)

MERGE_PDF_TOOL = Tool(
    name="MergePdf",
    description="Merge PDF files inside the Blaxel sandbox into one output under outputs/pdf/.",
    input_schema={
        "type": "object",
        "properties": {
            "output_path": {"type": "string", "description": "Sandbox-relative output .pdf path"},
            "inputs": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Sandbox-relative input PDF paths in merge order",
            },
        },
        "required": ["output_path", "inputs"],
    },
    handler=_merge_pdf,
    categories=["artifact", "pdf"],
)

ARTIFACT_BUILD_TOOLS: list[Tool] = [
    BUILD_DOCUMENT_TOOL,
    BUILD_PRESENTATION_TOOL,
    BUILD_SPREADSHEET_TOOL,
    MERGE_PDF_TOOL,
]

ARTIFACT_BUILD_TOOL_BY_TYPE: dict[str, Tool] = {
    "document": BUILD_DOCUMENT_TOOL,
    "presentation": BUILD_PRESENTATION_TOOL,
    "spreadsheet": BUILD_SPREADSHEET_TOOL,
    "pdf": MERGE_PDF_TOOL,
}
