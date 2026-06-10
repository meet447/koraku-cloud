"""Context pinning for compaction-aware tool results."""
from __future__ import annotations

from koraku.agent.context_manager import ContextManager
from koraku.agent.context_pins import (
    format_pinned_context,
    record_pins,
    should_pin_tool_result,
)
from koraku.core.models import AgentMessage, SessionState


def test_should_pin_delegate_and_paths() -> None:
    assert should_pin_tool_result(tool_name="ResearchRun", content="long summary", is_error=False)
    assert should_pin_tool_result(
        tool_name="Write",
        content="Wrote outputs/documents/report.pdf",
        is_error=False,
    )
    assert not should_pin_tool_result(tool_name="Read", content="short", is_error=False)


def test_compact_keeps_pinned_tool_pair() -> None:
    msgs = [
        AgentMessage(role="user", content=[{"type": "text", "text": "research"}]),
        AgentMessage(
            role="assistant",
            content=[{"type": "tool_use", "name": "ResearchRun", "id": "t1", "input": {}}],
        ),
        AgentMessage(
            role="user",
            content=[{"type": "tool_result", "tool_use_id": "t1", "content": "outputs/report.pdf created"}],
        ),
        AgentMessage(role="assistant", content=[{"type": "text", "text": "Done."}]),
    ]
    cm = ContextManager(compact_tool_rounds=True)
    out = cm.process_messages(msgs, pinned_tool_use_ids={"t1"})
    assert len(out) == 4


def test_record_pins_on_session() -> None:
    session = SessionState(session_id="s1")
    record_pins(
        session,
        [{"id": "t1", "name": "VerifyGoal"}],
        [{"tool_use_id": "t1", "content": "PASS\nAll criteria met.", "is_error": False}],
    )
    assert len(session.pinned_context) == 1
    block = format_pinned_context(session)
    assert block is not None
    assert "PASS" in block
