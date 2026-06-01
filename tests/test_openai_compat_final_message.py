"""Regression: ``assistant_message`` text must match streamed body when native tool_calls exist."""

from koraku.llm.providers.openai_compat_backend import _OpenAIStreamHandler


def test_assistant_message_uses_full_accumulated_text_with_native_tools():
    """``_parse_tool_calls_from_text`` can shrink long prose; final snapshot must not."""
    h = _OpenAIStreamHandler("accounts/fireworks/models/test")
    h.accumulated_text = "Here is a long email digest.\n\n" + ("Line of body.\n" * 80)
    h.native_tool_slots[0] = {"id": "call_1", "name": "ComposioRun", "arguments": "{}"}
    events = list(h.get_final_messages())
    am = next(e for e in events if e["type"] == "assistant_message")
    blocks = am["message"]["content"]
    assert blocks[0] == {"type": "text", "text": h.accumulated_text.strip()}
    assert blocks[1]["type"] == "tool_use"
    assert blocks[1]["name"] == "ComposioRun"
