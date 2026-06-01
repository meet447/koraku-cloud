from __future__ import annotations

import asyncio
import os
import tempfile

from koraku.tools.binary_read_paths import (
    file_extension_for_read_path,
    format_binary_read_response,
    is_binary_extension,
    should_use_binary_read_branch,
)


def test_extension_detection() -> None:
    assert file_extension_for_read_path("foo/bar.PDF") == "pdf"
    assert file_extension_for_read_path(r"a\b\doc.DOCX") == "docx"
    assert file_extension_for_read_path("README") == ""


def test_binary_extensions() -> None:
    assert is_binary_extension("pdf") is True
    assert is_binary_extension("tsx") is False


def test_should_use_binary_branch() -> None:
    assert should_use_binary_read_branch("/tmp/x.pdf") is True
    assert should_use_binary_read_branch("notes.md") is False


def test_format_binary_response_includes_hints() -> None:
    body = format_binary_read_response("report.pdf", 12345)
    assert "Binary file" in body
    assert "report.pdf" in body
    assert "12345" in body
    assert "Bash" in body
    assert "SKILL.md" in body


def test_read_tool_local_pdf_returns_guidance(monkeypatch) -> None:
    from koraku.core.config import settings
    from koraku.tools.registry import read_tool

    monkeypatch.setattr(settings, "host_file_tools_restrict_to_workspace", False)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        path = f.name
    try:
        out = asyncio.run(read_tool.run(file_path=path))
        assert "Binary file" in out
        assert path in out or os.path.basename(path) in out
    finally:
        os.unlink(path)
