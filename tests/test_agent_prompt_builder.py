"""Tiered prompts and SSE worker status traces."""
from __future__ import annotations

from koraku.agent.prompt_builder import build_tiered_system_prompt
from koraku.streaming.koraku_sse import KorakuStreamState, map_koraku_stream_events


def test_tiered_prompt_includes_stable_and_context() -> None:
    prompt = build_tiered_system_prompt(
        "/tmp/ws",
        learned_memory_prefetch="## Learned memory\n- User likes tea\n",
    )
    assert "sovereign digital mind" in prompt
    assert "Explicit preferences" in prompt or "User memory" in prompt
    assert "User likes tea" in prompt


def test_agent_trace_worker_status_maps_to_koraku_event() -> None:
    state = KorakuStreamState()
    rows = map_koraku_stream_events(
        {
            "type": "agent.trace",
            "data": {"trace": "worker_status", "message": "Running GMAIL_FETCH…", "tool": "GMAIL_FETCH"},
        },
        state,
    )
    assert len(rows) == 1
    assert rows[0]["type"] == "koraku.event"
    import json

    inner = json.loads(rows[0]["data"])
    assert inner["trace"] == "worker_status"
    assert "GMAIL" in inner["data"]["message"]
