"""iMessage progress bubble copy."""
from __future__ import annotations

from koraku.channels.imessage_progress import bubble_for_tool, message_for_agent_event


def test_bubble_for_web_search() -> None:
    msg = bubble_for_tool("WebSearch", {"query": "weather NYC"})
    assert msg is not None
    assert "Searching" in msg
    assert "weather" in msg


def test_skips_channel_send() -> None:
    assert bubble_for_tool("ChannelSend", {"message": "hi"}) is None


def test_tool_execution_event() -> None:
    msg = message_for_agent_event(
        {
            "type": "tool_execution",
            "data": {"tool": "Read", "input": {"file_path": "notes.md"}, "id": "t1"},
        },
    )
    assert msg is not None
    assert "notes.md" in msg
