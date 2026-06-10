"""Sandbox artifact dependency bootstrap helpers."""
from __future__ import annotations

from koraku.artifacts import blaxel_build as bb
from koraku.tools import blaxel_dispatch as bd


def test_require_python_import_fails_loudly() -> None:
    script = bb._require_python_import("pptx", package_hint="python-pptx")
    assert "import pptx" in script
    assert "python-pptx" in script
    assert "exit 1" in script
    assert "could not import pptx" in script


def test_sandbox_preamble_includes_artifact_packages() -> None:
    assert "python-docx" in bd._SANDBOX_PYTHON_PREAMBLE
    assert "python-pptx" in bd._SANDBOX_PYTHON_PREAMBLE
    assert "--no-cache-dir" in bd._SANDBOX_PYTHON_PREAMBLE
