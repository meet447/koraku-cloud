"""Koraku SSE maps tool calls to normalized lifecycle events."""

from __future__ import annotations

import json

from koraku.streaming import KorakuStreamState, map_koraku_stream_events


def test_agent_subagent_emits_koraku_subagent() -> None:
    state = KorakuStreamState()
    rows = map_koraku_stream_events(
        {
            "type": "agent.subagent",
            "data": {"phase": "composio_start", "toolkits": ["GMAIL"]},
            "subagent": {"composio": True, "toolkits": ["GMAIL"]},
        },
        state,
    )
    assert len(rows) == 1
    assert rows[0]["type"] == "koraku.subagent"
    assert rows[0]["data"]["phase"] == "composio_start"
    assert rows[0]["data"]["toolkits"] == ["GMAIL"]


def test_tool_execution_subagent_forwarded_to_inner_tool_event() -> None:
    state = KorakuStreamState()
    rows = map_koraku_stream_events(
        {
            "type": "tool_execution",
            "data": {
                "tool": "GMAIL_FETCH_EMAILS",
                "input": {"max_results": 5},
                "id": "call_inner_1",
                "mode": "sequential",
            },
            "subagent": {"composio": True, "toolkits": ["GMAIL"]},
        },
        state,
    )
    inner = json.loads(rows[0]["data"])
    assert inner["type"] == "tool_event"
    assert inner["subagent"] == {"composio": True, "toolkits": ["GMAIL"]}


def _inner(payload: dict) -> dict:
    assert payload["type"] == "koraku.event"
    return json.loads(payload["data"])


def test_tool_use_stream_chunks_are_not_forwarded() -> None:
    state = KorakuStreamState()

    assert map_koraku_stream_events(
        {
            "type": "stream_event",
            "event": {
                "type": "content_block_start",
                "index": 1,
                "content_block": {"type": "tool_use", "id": "t1", "name": "WebSearch"},
            },
        },
        state,
    ) == []
    assert map_koraku_stream_events(
        {
            "type": "stream_event",
            "event": {
                "type": "content_block_delta",
                "index": 1,
                "delta": {"type": "input_json_delta", "partial_json": '{"query":"x"}'},
            },
        },
        state,
    ) == []
    assert map_koraku_stream_events(
        {"type": "stream_event", "event": {"type": "content_block_stop", "index": 1}},
        state,
    ) == []


def test_tool_execution_and_result_become_tool_events() -> None:
    state = KorakuStreamState()

    started_rows = map_koraku_stream_events(
        {
            "type": "tool_execution",
            "data": {
                "tool": "WebSearch",
                "input": {"query": "koraku"},
                "id": "toolu_1",
                "mode": "sequential",
            },
        },
        state,
    )
    started = _inner(started_rows[0])
    assert started["type"] == "tool_event"
    assert started["phase"] == "started"
    assert started["status"] == "running"
    assert started["tool_use_id"] == "toolu_1"
    assert started["tool_name"] == "WebSearch"
    assert started["tool_input"] == {"query": "koraku"}

    completed_rows = map_koraku_stream_events(
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_1",
                        "content": "result " * 200,
                        "is_error": False,
                    }
                ],
            },
        },
        state,
    )
    completed = _inner(completed_rows[0])
    assert completed["type"] == "tool_event"
    assert completed["phase"] == "completed"
    assert completed["status"] == "completed"
    assert completed["tool_name"] == "WebSearch"
    assert completed["is_error"] is False
    assert len(completed["output_summary"]) <= 500
    assert completed.get("truncated", {}).get("result") is True


def test_assistant_message_tool_calls_are_redacted_but_text_streams() -> None:
    state = KorakuStreamState()

    rows = map_koraku_stream_events(
        {
            "type": "stream_event",
            "event": {
                "type": "assistant_message",
                "message": {
                    "content": [
                        {"type": "text", "text": "I will check."},
                        {"type": "tool_use", "id": "toolu_1", "name": "WebSearch", "input": {"query": "x"}},
                    ]
                },
            },
        },
        state,
    )

    inner = _inner(rows[0])
    content = inner["event"]["message"]["content"]
    assert content == [{"type": "text", "text": "I will check."}]


def test_input_json_delta_is_never_forwarded_even_without_start() -> None:
    state = KorakuStreamState()

    rows = map_koraku_stream_events(
        {
            "type": "stream_event",
            "event": {
                "type": "content_block_delta",
                "index": 9,
                "delta": {"type": "input_json_delta", "partial_json": '{"file_path": "x.md"}'},
            },
        },
        state,
    )

    assert rows == []


def test_started_payload_includes_run_id() -> None:
    state = KorakuStreamState()
    state.run_id = "run-test-abc"
    out = state.started_payload("claude-3", chat_session_id="sess-1")
    assert out["data"]["runId"] == "run-test-abc"
    assert out["data"]["chatSessionId"] == "sess-1"


def test_agent_cancelled_emits_completion_with_cancelled_flag() -> None:
    state = KorakuStreamState()
    state.resolved_model = "m1"
    rows = map_koraku_stream_events(
        {"type": "agent.cancelled", "data": {"reason": "client_disconnect", "run_id": "r1"}},
        state,
    )
    assert len(rows) >= 2
    assert rows[0]["type"] == "koraku.event"
    inner_result = json.loads(str(rows[0]["data"]))
    assert inner_result["type"] == "result"
    assert inner_result["subtype"] == "cancelled"
    assert rows[1]["type"] == "koraku.completed"
    assert rows[1]["data"]["cancelled"] is True
