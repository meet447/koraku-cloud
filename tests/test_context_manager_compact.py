"""ContextManager: optional compaction of tool rounds for LLM context."""

from __future__ import annotations

from koraku.agent.context_manager import ContextManager
from koraku.core.models import AgentMessage


def test_compact_drops_completed_tool_pair_before_final_text() -> None:
    msgs = [
        AgentMessage(role="user", content=[{"type": "text", "text": "read foo"}]),
        AgentMessage(
            role="assistant",
            content=[{"type": "tool_use", "name": "Read", "id": "t1", "input": {"path": "foo"}}],
        ),
        AgentMessage(
            role="user",
            content=[{"type": "tool_result", "tool_use_id": "t1", "content": "file contents"}],
        ),
        AgentMessage(role="assistant", content=[{"type": "text", "text": "Here is what foo says."}]),
    ]
    cm = ContextManager(compact_tool_rounds=True)
    out = cm.process_messages(msgs)
    roles = [m.role for m in out]
    assert roles == ["user", "assistant"]
    assert out[0].content[0]["text"] == "read foo"  # type: ignore[index]
    assert "foo says" in out[1].content[0]["text"]  # type: ignore[index]


def test_compact_keeps_trailing_open_tool_round() -> None:
    msgs = [
        AgentMessage(role="user", content=[{"type": "text", "text": "go"}]),
        AgentMessage(
            role="assistant",
            content=[{"type": "tool_use", "name": "Read", "id": "t1", "input": {}}],
        ),
        AgentMessage(
            role="user",
            content=[{"type": "tool_result", "tool_use_id": "t1", "content": "x"}],
        ),
    ]
    cm = ContextManager(compact_tool_rounds=True)
    out = cm.process_messages(msgs)
    assert len(out) == 3


def test_compact_keeps_tool_pair_when_followed_by_user_nudge() -> None:
    msgs = [
        AgentMessage(role="user", content=[{"type": "text", "text": "tell me about the booking"}]),
        AgentMessage(
            role="assistant",
            content=[{"type": "tool_use", "name": "GMAIL_FETCH_EMAILS", "id": "t1", "input": {}}],
        ),
        AgentMessage(
            role="user",
            content=[{
                "type": "tool_result",
                "tool_use_id": "t1",
                "content": "Punjab Grill booking for 2:45 PM, party of 2.",
            }],
        ),
        AgentMessage(role="user", content=[{"type": "text", "text": "??"}]),
    ]
    cm = ContextManager(compact_tool_rounds=True)
    out = cm.process_messages(msgs)
    assert len(out) == 4
    assert out[2].content[0]["content"].startswith("Punjab Grill")  # type: ignore[index]


def test_compact_keeps_unresolved_tool_pair_even_after_generic_followup_answer() -> None:
    msgs = [
        AgentMessage(role="user", content=[{"type": "text", "text": "tell me about the booking"}]),
        AgentMessage(
            role="assistant",
            content=[{"type": "tool_use", "name": "GMAIL_FETCH_EMAILS", "id": "t1", "input": {}}],
        ),
        AgentMessage(
            role="user",
            content=[{
                "type": "tool_result",
                "tool_use_id": "t1",
                "content": "Punjab Grill booking for 2:45 PM, party of 2.",
            }],
        ),
        AgentMessage(role="user", content=[{"type": "text", "text": "??"}]),
        AgentMessage(role="assistant", content=[{"type": "text", "text": "How can I help?"}]),
    ]
    cm = ContextManager(compact_tool_rounds=True)
    out = cm.process_messages(msgs)
    assert len(out) == 5
    assert out[2].content[0]["content"].startswith("Punjab Grill")  # type: ignore[index]


def test_compact_disabled_keeps_tool_pairs() -> None:
    msgs = [
        AgentMessage(role="user", content=[{"type": "text", "text": "q"}]),
        AgentMessage(
            role="assistant",
            content=[{"type": "tool_use", "name": "Read", "id": "t1", "input": {}}],
        ),
        AgentMessage(
            role="user",
            content=[{"type": "tool_result", "tool_use_id": "t1", "content": "x"}],
        ),
        AgentMessage(role="assistant", content=[{"type": "text", "text": "a"}]),
    ]
    cm = ContextManager(compact_tool_rounds=False)
    out = cm.process_messages(msgs)
    assert len(out) == 4


def test_summary_preserves_visible_artifact_reference_for_later_followup() -> None:
    msgs = [
        AgentMessage(role="user", content=[{"type": "text", "text": "fetch latest news and save it as md"}]),
        AgentMessage(
            role="assistant",
            content=[{"type": "tool_use", "name": "WebSearch", "id": "news1", "input": {}}],
        ),
        AgentMessage(
            role="user",
            content=[{"type": "tool_result", "tool_use_id": "news1", "content": "Top headlines..."}],
        ),
        AgentMessage(
            role="assistant",
            content=[{"type": "tool_use", "name": "Write", "id": "news2", "input": {}}],
        ),
        AgentMessage(
            role="user",
            content=[{"type": "tool_result", "tool_use_id": "news2", "content": "Saved file"}],
        ),
        AgentMessage(
            role="assistant",
            content=[{
                "type": "text",
                "text": "I've fetched the latest headlines and saved latest_news_2026-04-25.md.",
            }],
        ),
        AgentMessage(role="user", content=[{"type": "text", "text": "fetch my latest mails"}]),
        AgentMessage(
            role="assistant",
            content=[{"type": "tool_use", "name": "GMAIL_FETCH_EMAILS", "id": "mail1", "input": {}}],
        ),
        AgentMessage(
            role="user",
            content=[{
                "type": "tool_result",
                "tool_use_id": "mail1",
                "content": "Sarthak email: sarthakthopate265@gmail.com",
            }],
        ),
        AgentMessage(role="assistant", content=[{"type": "text", "text": "Sarthak's email is available."}]),
        AgentMessage(role="user", content=[{"type": "text", "text": "thanks"}]),
        AgentMessage(role="assistant", content=[{"type": "text", "text": "You're welcome."}]),
        AgentMessage(role="user", content=[{"type": "text", "text": "anything else"}]),
        AgentMessage(role="assistant", content=[{"type": "text", "text": "No."}]),
        AgentMessage(role="user", content=[{"type": "text", "text": "cool"}]),
        AgentMessage(role="assistant", content=[{"type": "text", "text": "Sure."}]),
        AgentMessage(role="user", content=[{"type": "text", "text": "send sarthak this news"}]),
    ]
    cm = ContextManager(summarize_after=10, compact_tool_rounds=True)
    out = cm.process_messages(msgs)
    assert isinstance(out[1].content, str)
    assert "latest_news_2026-04-25.md" in out[1].content
    assert "send sarthak this news" in out[-1].content[0]["text"]  # type: ignore[index]
