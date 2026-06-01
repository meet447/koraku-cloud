"""Classify tool stdout strings so the agent marks real failures as tool_result.is_error."""

from __future__ import annotations


def tool_stdout_indicates_error(text: str, *, tool_name: str) -> bool:
    """Return True when the tool output should be surfaced as is_error to the model."""
    raw = text if isinstance(text, str) else str(text)
    s = raw.strip()
    if not s:
        # Empty fetch/search is almost never usable grounding.
        return tool_name in ("WebSearch", "WebFetch", "WebPage")

    lowered = s.lower()

    if lowered.startswith("error:") or lowered.startswith("error "):
        return True

    leaders = (
        "failed",
        "blocked",
        "search failed",
        "fetch error",
        "file not found",
        "dir not found",
        "timeout after",
        "old_string not found",
        "connection error",
        "api error",
    )
    if any(lowered.startswith(p) for p in leaders):
        return True

    # Grep / similar: intentional non-hit
    if lowered.startswith("no matches"):
        return False

    return False
