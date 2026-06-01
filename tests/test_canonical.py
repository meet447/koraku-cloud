from koraku.llm.canonical import (
    anthropic_tool_definitions,
    build_compact_tool_prompt,
    openai_chat_messages_from_agent_messages,
    anthropic_messages_from_agent_messages,
    CanonicalChatRequest,
)
from koraku.core.models import AgentMessage

class DummyTool:
    def to_anthropic_schema(self):
        return {"name": "dummy_tool", "input_schema": {"type": "object", "properties": {}}}

    def to_compact_prompt(self):
        return "dummy_tool: A dummy tool"

def test_anthropic_tool_definitions():
    # Test with None
    assert anthropic_tool_definitions(None) == []

    # Test with empty list
    assert anthropic_tool_definitions([]) == []

    # Test with object having to_anthropic_schema
    obj = DummyTool()
    res = anthropic_tool_definitions([obj])
    assert res == [{"name": "dummy_tool", "input_schema": {"type": "object", "properties": {}}}]

    # Test with dict having name and input_schema
    d = {"name": "dict_tool", "input_schema": {"type": "object"}, "extra": "ignored but kept"}
    res2 = anthropic_tool_definitions([d])
    assert res2 == [d]

    # Test with dict missing name or input_schema
    assert anthropic_tool_definitions([{"name": "only_name"}]) == []
    assert anthropic_tool_definitions([{"input_schema": {}}]) == []

    # Test with mixed
    res3 = anthropic_tool_definitions([obj, d, {"invalid": 1}])
    assert len(res3) == 2
    assert res3[0]["name"] == "dummy_tool"
    assert res3[1]["name"] == "dict_tool"

def test_build_compact_tool_prompt():
    # Test with no tools
    res = build_compact_tool_prompt([])
    assert "Call tools when needed" in res

    # Test with DummyTool
    res2 = build_compact_tool_prompt([DummyTool()])
    assert "dummy_tool: A dummy tool" in res2

    # Test with dict tool
    res3 = build_compact_tool_prompt([{"name": "my_tool", "description": "Does a thing"}])
    assert "my_tool: Does a thing" in res3

    # Test with unknown dict
    res4 = build_compact_tool_prompt([{}])
    assert "Unknown: " in res4

def test_openai_chat_messages_from_agent_messages():
    msgs = [
        AgentMessage(role="user", content="Hello"),
        AgentMessage(role="assistant", content=[
            {"type": "text", "text": "Sure!"},
            {"type": "tool_use", "name": "my_tool", "input": {"x": 1}},
        ]),
        AgentMessage(role="user", content=[
            {"type": "tool_result", "tool_use_id": "call_123", "content": "Result 1"}
        ]),
        AgentMessage(role="user", content=[
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "abcd"}},
            {"type": "text", "text": "What is this?"}
        ])
    ]
    res = openai_chat_messages_from_agent_messages(msgs)
    assert len(res) == 4

    assert res[0] == {"role": "user", "content": "Hello"}

    assert res[1]["role"] == "assistant"
    assert "[Call my_tool]:\n{\"x\": 1}" in res[1]["content"]
    assert "Sure!" in res[1]["content"]

    assert res[2]["role"] == "user"
    assert "[Result call_123]:\nResult 1" in res[2]["content"]

    assert res[3]["role"] == "user"
    assert isinstance(res[3]["content"], list)
    assert res[3]["content"][0] == {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,abcd"}}
    assert res[3]["content"][1] == {"type": "text", "text": "What is this?"}

def test_anthropic_messages_from_agent_messages():
    msgs = [
        AgentMessage(role="user", content="Hello"),
        AgentMessage(role="assistant", content="Hi there")
    ]
    res = anthropic_messages_from_agent_messages(msgs)
    assert res == [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"}
    ]

def test_canonical_chat_request():
    msgs = [AgentMessage(role="user", content="Hi")]
    req = CanonicalChatRequest.for_turn(
        model_id="my-model",
        messages=msgs,
        tool_schemas=[{"name": "t1", "input_schema": {}}],
        system_prompt="You are an assistant"
    )

    anth_kwargs = req.anthropic_stream_kwargs()
    assert anth_kwargs["model"] == "my-model"
    assert anth_kwargs["system"] == "You are an assistant"
    assert "tools" in anth_kwargs
    assert anth_kwargs["tools"][0]["name"] == "t1"

    openai_body = req.openai_chat_completions_body()
    assert openai_body["model"] == "my-model"
    assert openai_body["messages"][0]["role"] == "system"
    assert "TOOLS: Emit exactly one JSON object" in openai_body["messages"][0]["content"]
    assert openai_body["messages"][1]["role"] == "user"
