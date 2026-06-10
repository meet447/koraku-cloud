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

    started = map_koraku_stream_events(
        {
            "type": "stream_event",
            "event": {
                "type": "content_block_start",
                "index": 1,
                "content_block": {"type": "tool_use", "id": "t1", "name": "WebSearch"},
            },
        },
        state,
    )
    assert len(started) == 1
    inner = _inner(started[0])
    assert inner["type"] == "tool_event"
    assert inner["phase"] == "started"
    assert inner["tool_name"] == "WebSearch"
    assert inner["tool_use_id"] == "t1"

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


def test_tool_use_pending_emits_started_tool_event() -> None:
    state = KorakuStreamState()
    rows = map_koraku_stream_events(
        {
            "type": "stream_event",
            "event": {
                "type": "tool_use_pending",
                "tool_use_id": "call_write_1",
                "name": "Write",
                "input": {"file_path": "notes.md"},
            },
        },
        state,
    )
    assert len(rows) == 1
    inner = _inner(rows[0])
    assert inner["phase"] == "started"
    assert inner["tool_name"] == "Write"
    assert inner["tool_use_id"] == "call_write_1"
    assert inner["tool_input"] == {"file_path": "notes.md"}


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


def test_artifact_subagent_payload_from_compilation_context() -> None:
    state = KorakuStreamState()
    rows = map_koraku_stream_events(
        {
            "type": "tool_execution",
            "data": {
                "target_capability": "BuildDocument",
                "evaluation_parameters": {"output_path": "outputs/documents/a.docx"},
                "execution_id": "call_doc_1",
            },
            "subprocess_context": {"workhorse": "document", "format_target": "document"},
        },
        state,
    )
    inner = json.loads(rows[0]["data"])
    assert inner["subagent"] == {"workhorse": "document"}
    assert inner["tool_name"] == "BuildDocument"
    assert inner["tool_use_id"] == "workhorse:call_doc_1"


def test_compilation_start_normalizes_to_workhorse_start() -> None:
    state = KorakuStreamState()
    rows = map_koraku_stream_events(
        {
            "type": "agent.subagent",
            "data": {"subprocess_phase": "compilation_start", "format_target": "presentation"},
            "subprocess_context": {"compilation_active": True, "format_target": "presentation"},
        },
        state,
    )
    assert rows[0]["data"]["phase"] == "workhorse_start"
    assert rows[0]["data"]["workhorse"] == "presentation"


def test_composio_subagent_completed_does_not_emit_top_level_completion() -> None:
    state = KorakuStreamState()
    rows = map_koraku_stream_events(
        {
            "type": "agent.completed",
            "data": {"reason": "end_turn", "steps": 1, "mode": "composio_sub"},
            "subagent": {"composio": True, "toolkits": ["GMAIL"]},
        },
        state,
    )
    assert rows == []


def test_workhorse_subagent_payload_from_subprocess_context() -> None:
    state = KorakuStreamState()
    rows = map_koraku_stream_events(
        {
            "type": "tool_execution",
            "data": {
                "tool": "WebSearch",
                "input": {"query": "nifty 50"},
                "id": "tool_1",
                "mode": "sequential",
            },
            "subprocess_context": {"workhorse": "research"},
        },
        state,
    )
    inner = _inner(rows[0])
    assert inner["subagent"] == {"workhorse": "research"}
    assert inner["tool_use_id"] == "workhorse:tool_1"


def test_workhorse_subagent_start_normalizes_phase() -> None:
    state = KorakuStreamState()
    rows = map_koraku_stream_events(
        {
            "type": "agent.subagent",
            "data": {"phase": "start", "worker": "research"},
            "subprocess_context": {"workhorse": "research"},
        },
        state,
    )
    assert len(rows) == 1
    assert rows[0]["type"] == "koraku.subagent"
    assert rows[0]["data"]["phase"] == "workhorse_start"
    assert rows[0]["data"]["workhorse"] == "research"


def test_composio_subagent_start_from_subprocess_phase() -> None:
    state = KorakuStreamState()
    rows = map_koraku_stream_events(
        {
            "type": "agent.subagent",
            "data": {"subprocess_phase": "initialization", "active_scopes": ["GMAIL"]},
            "subprocess_context": {"integration_active": True, "active_scopes": ["GMAIL"]},
        },
        state,
    )
    assert rows[0]["data"]["phase"] == "composio_start"
    assert rows[0]["data"]["toolkits"] == ["GMAIL"]
    assert rows[0]["data"]["composio"] is True


def test_workhorse_subagent_completed_does_not_emit_top_level_completion() -> None:
    state = KorakuStreamState()
    rows = map_koraku_stream_events(
        {
            "type": "agent.completed",
            "data": {"reason": "end_turn", "steps": 2, "mode": "research_sub_loop"},
            "subprocess_context": {"workhorse": "research"},
        },
        state,
    )
    assert rows == []


def test_composio_subagent_tool_ids_are_namespaced() -> None:
    state = KorakuStreamState()
    sub = {"composio": True, "toolkits": ["GMAIL"]}

    parent_started = map_koraku_stream_events(
        {
            "type": "tool_execution",
            "data": {"tool": "ComposioRun", "input": {"goal": "x"}, "id": "tool_0", "mode": "sequential"},
        },
        state,
    )
    parent_inner = _inner(parent_started[0])
    assert parent_inner["tool_use_id"] == "tool_0"
    assert parent_inner["tool_name"] == "ComposioRun"

    inner_started = map_koraku_stream_events(
        {
            "type": "tool_execution",
            "data": {
                "tool": "GMAIL_FETCH_EMAILS",
                "input": {"max_results": 5},
                "id": "tool_0",
                "mode": "sequential",
            },
            "subagent": sub,
        },
        state,
    )
    inner_inner = _inner(inner_started[0])
    assert inner_inner["tool_use_id"] == "composio:tool_0"
    assert inner_inner["tool_name"] == "GMAIL_FETCH_EMAILS"
    assert inner_inner["subagent"] == {"composio": True, "toolkits": ["GMAIL"]}

    inner_done = map_koraku_stream_events(
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "tool_0",
                        "content": "ok",
                        "is_error": False,
                    }
                ],
            },
            "subagent": sub,
        },
        state,
    )
    inner_completed = _inner(inner_done[0])
    assert inner_completed["tool_use_id"] == "composio:tool_0"
    assert inner_completed["tool_name"] == "GMAIL_FETCH_EMAILS"

    parent_done = map_koraku_stream_events(
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "tool_0",
                        "content": "parent result",
                        "is_error": False,
                    }
                ],
            },
        },
        state,
    )
    parent_completed = _inner(parent_done[0])
    assert parent_completed["tool_use_id"] == "tool_0"
    assert parent_completed["tool_name"] == "ComposioRun"
