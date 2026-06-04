"""Conventional output paths for workspace artifacts."""
from __future__ import annotations

import os
from pathlib import Path

ARTIFACT_SUBDIRS = {
    "document": "outputs/documents",
    "presentation": "outputs/presentations",
    "spreadsheet": "outputs/spreadsheets",
    "pdf": "outputs/pdf",
}


def ensure_artifact_dirs(workspace: str) -> None:
    root = Path(workspace).resolve()
    for sub in ARTIFACT_SUBDIRS.values():
        (root / sub).mkdir(parents=True, exist_ok=True)
    templates = root / ".koraku" / "templates"
    templates.mkdir(parents=True, exist_ok=True)


def artifact_output_dir(workspace: str, artifact_type: str) -> str:
    sub = ARTIFACT_SUBDIRS.get(artifact_type, "outputs")
    return str(Path(workspace).resolve() / sub)
