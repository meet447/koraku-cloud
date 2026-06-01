"""Heuristics to reduce time-to-first-token on simple chat turns."""
from __future__ import annotations

# Substrings that imply file / shell / workspace work (do not defer Blaxel provisioning).
_FILE_WORKSPACE_MARKERS: tuple[str, ...] = (
    "workspace",
    "save to",
    "save it",
    "write to",
    "write a",
    "create a file",
    "create file",
    "read file",
    "open file",
    ".md",
    ".txt",
    ".csv",
    ".json",
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".html",
    ".pdf",
    "bash",
    "shell",
    "script",
    "folder",
    "directory",
    "download",
    "upload",
    "/tmp/",
    " in my ",
)


def should_defer_blaxel_provision(*, message: str, has_images: bool) -> bool:
    """Skip upfront Blaxel VM work for short, conversational turns without file intent."""
    if has_images:
        return False
    text = (message or "").strip().lower()
    if not text:
        return False
    words = text.split()
    if len(words) > 28:
        return False
    if any(marker in text for marker in _FILE_WORKSPACE_MARKERS):
        return False
    return True
