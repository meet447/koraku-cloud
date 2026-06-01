"""Tests for native OpenAI tool calling and inline tool-call parsing."""

import json

from koraku.core.models import AgentMessage
from koraku.llm.canonical import (
    CanonicalChatRequest,
    openai_chat_messages_from_agent_messages,
    openai_tool_definitions,
)
from koraku.llm.tool_call_parse import parse_tool_calls_from_text
from koraku.tools.tool_def import Tool


async def _noop(**kwargs: object) -> str:
    return "ok"


def test_openai_tool_definitions_from_tool():
    tool = Tool(
        name="Write",
        description="Write a file",
        input_schema={
            "type": "object",
            "properties": {"file_path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["file_path", "content"],
        },
        handler=_noop,
    )
    defs = openai_tool_definitions([tool])
    assert defs == [{
        "type": "function",
        "function": {
            "name": "Write",
            "description": "Write a file",
            "parameters": tool.input_schema,
        },
    }]


def test_openai_messages_use_native_tool_calls_not_call_markers():
    msgs = [
        AgentMessage(role="assistant", content=[
            {"type": "text", "text": "Creating the guide."},
            {"type": "tool_use", "id": "call_write_1", "name": "Write", "input": {"file_path": "a.md", "content": "hi"}},
        ]),
        AgentMessage(role="user", content=[
            {"type": "tool_result", "tool_use_id": "call_write_1", "content": "Wrote 2 chars to a.md"},
        ]),
    ]
    out = openai_chat_messages_from_agent_messages(msgs)
    assert out[0]["role"] == "assistant"
    assert out[0]["content"] == "Creating the guide."
    assert out[0]["tool_calls"][0]["id"] == "call_write_1"
    assert out[0]["tool_calls"][0]["function"]["name"] == "Write"
    assert json.loads(out[0]["tool_calls"][0]["function"]["arguments"]) == {
        "file_path": "a.md",
        "content": "hi",
    }
    assert "[Call Write]" not in json.dumps(out)
    assert out[1] == {
        "role": "tool",
        "tool_call_id": "call_write_1",
        "content": "Wrote 2 chars to a.md",
    }


def test_openai_chat_completions_body_includes_native_tools(monkeypatch):
    monkeypatch.setattr("koraku.llm.canonical.settings.chat_openai_native_tools", True)

    class DummyTool:
        def to_openai_schema(self):
            return {"type": "function", "function": {"name": "Write", "description": "x", "parameters": {}}}

    req = CanonicalChatRequest.for_turn(
        model_id="accounts/fireworks/models/test",
        messages=[AgentMessage(role="user", content="hi")],
        tool_schemas=[DummyTool()],
        system_prompt="You are helpful",
    )
    body = req.openai_chat_completions_body()
    assert body["tool_choice"] == "auto"
    assert body["tools"][0]["function"]["name"] == "Write"
    assert "TOOLS: Emit exactly one JSON object" not in body["messages"][0]["content"]
    assert "function calling" in body["messages"][0]["content"].lower()


def test_parse_call_write_with_large_markdown_content():
    content = "# Title\n\n" + ("Long paragraph with braces {not json}.\n" * 200)
    payload = json.dumps({"file_path": "ai-pc-build-70k-guide.md", "content": content}, ensure_ascii=False)
    text = f"Creating the guide now.\n[Call Write]: {payload}\nDone."
    blocks = parse_tool_calls_from_text(text)

    tool_blocks = [b for b in blocks if b.get("type") == "tool_use"]
    assert len(tool_blocks) == 1
    assert tool_blocks[0]["name"] == "Write"
    assert tool_blocks[0]["input"]["file_path"] == "ai-pc-build-70k-guide.md"
    assert tool_blocks[0]["input"]["content"] == content
    assert blocks[0]["text"] == "Creating the guide now."
    assert blocks[-1]["text"] == "Done."


def test_parse_compact_tool_json_with_nested_braces_in_content():
    payload = json.dumps({
        "tool": "Write",
        "parameters": {"file_path": "x.md", "content": "code: if (x) { return 1; }"},
    })
    blocks = parse_tool_calls_from_text(payload)
    assert blocks == [{
        "type": "tool_use",
        "id": "tool_0",
        "name": "Write",
        "input": {"file_path": "x.md", "content": "code: if (x) { return 1; }"},
    }]
