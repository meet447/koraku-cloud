"""Tests for artifact builders and sub-agent helpers."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from koraku.agent.budget import (
    artifact_max_rounds_for_goal,
    classify_artifact_goal,
    tools_for_artifact_worker,
)
from koraku.artifacts.docx_build import build_docx
from koraku.artifacts.paths import artifact_output_dir, ensure_artifact_dirs
from koraku.artifacts.pptx_build import build_pptx
from koraku.artifacts.xlsx_build import build_xlsx
from koraku.integrations.artifact_prompt import artifact_dispatcher_prompt_section
from koraku.tools.artifact_delegate_tool import ARTIFACT_RUN_TOOLS, ARTIFACT_TOOL_NAMES
from koraku.tools.registry import tools_for_execution_target


pytest.importorskip("docx")
pytest.importorskip("pptx")
pytest.importorskip("openpyxl")


def test_classify_artifact_goal_simple():
    assert classify_artifact_goal("one page memo about parking") == "artifact_simple"


def test_classify_artifact_goal_compose():
    assert classify_artifact_goal("10 slide deck with sections for QBR") == "artifact_compose"


def test_artifact_max_rounds_respects_simple():
    assert artifact_max_rounds_for_goal("brief memo") >= 2


def test_tools_for_artifact_worker_scopes_presentation():
    base = tools_for_execution_target("local")
    scoped = tools_for_artifact_worker(base, artifact_type="presentation", goal="short deck")
    names = {t.name for t in scoped}
    assert "BuildPresentation" in names
    assert "Write" in names
    assert "PresentationRun" not in names
    assert "ComposioRun" not in names


def test_artifact_delegate_tools_registered():
    assert ARTIFACT_TOOL_NAMES == (
        "DocumentRun",
        "PresentationRun",
        "SpreadsheetRun",
        "PdfRun",
    )
    assert len(ARTIFACT_RUN_TOOLS) == 4


def test_artifact_dispatcher_prompt_mentions_workers():
    text = artifact_dispatcher_prompt_section()
    assert "DocumentRun" in text
    assert "outputs/documents" in text


def test_ensure_artifact_dirs_and_output_path():
    with tempfile.TemporaryDirectory() as tmp:
        ensure_artifact_dirs(tmp)
        out = artifact_output_dir(tmp, "document")
        assert out.endswith("outputs/documents")
        assert Path(out).is_dir()


def test_build_docx_creates_file():
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "memo.docx")
        spec = {
            "title": "Test Memo",
            "sections": [{"heading": "Intro", "body": "Hello world."}],
        }
        result = build_docx(spec, path)
        assert Path(result).is_file()
        assert Path(result).stat().st_size > 0


def test_build_pptx_creates_file():
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "deck.pptx")
        spec = {
            "title": "Demo",
            "slides": [{"title": "Slide 1", "body": ["Point A", "Point B"]}],
        }
        result = build_pptx(spec, path)
        assert Path(result).is_file()


def test_build_xlsx_creates_file():
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "sheet.xlsx")
        spec = {"headers": ["A", "B"], "rows": [[1, 2], [3, 4]]}
        result = build_xlsx(spec, path)
        assert Path(result).is_file()

def test_build_presentation_tool_sandbox_only(monkeypatch):
    import asyncio

    async def _ok_gate() -> None:
        return None

    async def _fake_build(artifact_type: str, spec: dict, output_rel: str) -> str:
        assert artifact_type == "presentation"
        assert spec.get("title") == "LLM Basics"
        return json.dumps({"ok": True, "path": output_rel, "type": "pptx", "slides": 2})

    monkeypatch.setattr(
        "koraku.tools.artifact_build_tools.require_sandbox_for_artifacts",
        _ok_gate,
    )
    monkeypatch.setattr(
        "koraku.artifacts.blaxel_build.blaxel_build_artifact",
        _fake_build,
    )
    from koraku.tools.artifact_build_tools import _build_presentation

    spec = json.dumps(
        {
            "title": "LLM Basics",
            "slides": [{"title": "What is an LLM?", "body": ["Neural network", "Trained on text"]}],
        }
    )
    result = asyncio.run(
        _build_presentation(output_path="outputs/presentations/test-deck.pptx", spec=spec)
    )
    payload = json.loads(result)
    assert payload["ok"] is True
    assert payload["path"] == "outputs/presentations/test-deck.pptx"


@pytest.mark.asyncio
async def test_require_sandbox_rejects_local_execution():
    from koraku.agent.runtime_context import bind_execution_target, reset_execution_target
    from koraku.artifacts.sandbox_gate import require_sandbox_for_artifacts

    tok = bind_execution_target("local")
    try:
        err = await require_sandbox_for_artifacts()
    finally:
        reset_execution_target(tok)
    assert err is not None
    assert "sandbox-only" in err.lower()


def test_docx_build_cli_main(capsys):
    from koraku.artifacts import docx_build

    with tempfile.TemporaryDirectory() as tmp:
        out = str(Path(tmp) / "cli.docx")
        rc = docx_build.main(["--out", out, "--title", "CLI Test"])
        assert rc == 0
        captured = capsys.readouterr()
        payload = json.loads(captured.out.strip())
        assert payload["ok"] is True
        assert Path(payload["path"]).is_file()
