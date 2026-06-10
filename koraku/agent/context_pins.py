"""Pin critical tool results so context compaction does not drop them."""
from __future__ import annotations

import re
from typing import Any

from koraku.core.config import settings
from koraku.core.models import SessionState

_PIN_DELEGATE_TOOLS = frozenset(
    {
        "ComposioRun",
        "ResearchRun",
        "CodeRun",
        "VerifyGoal",
        "DocumentRun",
        "PresentationRun",
        "SpreadsheetRun",
        "PdfRun",
        "ParallelRun",
        "SkillLoad",
    }
)

_PATH_RE = re.compile(
    r"(?:outputs/|uploads/)[\w./-]+\.(?:pdf|docx|pptx|xlsx|csv|py|json|md|txt)|"
    r"[\w./-]+\.(?:pdf|docx|pptx|xlsx)",
    re.I,
)
_ID_RE = re.compile(r"\b(?:message_id|event_id|thread_id|id)[:\s]+[\w-]{4,}", re.I)


def context_pinning_enabled() -> bool:
    return bool(getattr(settings, "context_pin_tool_results", True))


def should_pin_tool_result(*, tool_name: str, content: str, is_error: bool) -> bool:
    if not context_pinning_enabled():
        return False
    name = (tool_name or "").strip()
    if name in _PIN_DELEGATE_TOOLS:
        return True
    text = (content or "").strip()
    if not text:
        return is_error
    if is_error or text.lower().startswith("error:"):
        return True
    if text.startswith("PASS") or text.startswith("FAIL"):
        return True
    if _PATH_RE.search(text):
        return True
    if _ID_RE.search(text):
        return True
    if name in ("Write", "Edit", "Bash") and ("outputs/" in text or "wrote" in text.lower()):
        return True
    return False


def _pin_summary(tool_name: str, content: str, *, is_error: bool) -> str:
    from koraku.agent.utils import _clean_one_line

    cap = int(getattr(settings, "context_pinned_summary_chars", 900))
    prefix = f"{tool_name}: "
    if is_error:
        return prefix + _clean_one_line(content, cap)
    return prefix + _clean_one_line(content, cap)


def record_pins(
    session: SessionState,
    tool_uses: list[dict[str, Any]],
    tool_results: list[dict[str, Any]],
) -> None:
    """Append pin entries on the session for compaction-aware context."""
    if not context_pinning_enabled():
        return
    use_by_id = {str(tu.get("id") or ""): tu for tu in tool_uses if tu.get("id")}
    max_items = max(4, int(getattr(settings, "context_pinned_max_items", 24)))
    existing_ids = {str(p.get("tool_use_id") or "") for p in session.pinned_context}

    for tr in tool_results:
        tool_use_id = str(tr.get("tool_use_id") or "").strip()
        if not tool_use_id or tool_use_id in existing_ids:
            continue
        tu = use_by_id.get(tool_use_id) or {}
        tool_name = str(tu.get("name") or "tool").strip() or "tool"
        content = tr.get("content", "")
        is_error = bool(tr.get("is_error"))
        text = content if isinstance(content, str) else str(content)
        if not should_pin_tool_result(tool_name=tool_name, content=text, is_error=is_error):
            continue
        session.pinned_context.append(
            {
                "tool_use_id": tool_use_id,
                "tool": tool_name,
                "summary": _pin_summary(tool_name, text, is_error=is_error),
            }
        )
        existing_ids.add(tool_use_id)

    if len(session.pinned_context) > max_items:
        session.pinned_context = session.pinned_context[-max_items:]


def pinned_tool_use_ids(session: SessionState) -> set[str]:
    return {str(p.get("tool_use_id") or "").strip() for p in session.pinned_context if p.get("tool_use_id")}


def format_pinned_context(session: SessionState) -> str | None:
    if not session.pinned_context:
        return None
    lines = [
        "## Pinned context (do not contradict)",
        "These tool outcomes were marked critical for this chat. Prefer them over dropped history.",
    ]
    cap = int(getattr(settings, "context_pinned_total_chars", 4000))
    total = sum(len(x) + 1 for x in lines)
    for pin in session.pinned_context[-24:]:
        tool = str(pin.get("tool") or "tool")
        summary = str(pin.get("summary") or "").strip()
        line = f"- **{tool}**: {summary}"
        if total + len(line) + 1 > cap:
            lines.append("- …additional pins truncated")
            break
        lines.append(line)
        total += len(line) + 1
    return "\n".join(lines)
