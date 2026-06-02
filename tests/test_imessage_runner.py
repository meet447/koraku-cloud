"""iMessage turn helpers."""
from __future__ import annotations

from koraku.core.models import SessionState
from koraku.integrations.supermemory_client import extract_last_assistant_text


def test_extract_last_assistant_text_from_block_content() -> None:
    session = SessionState(session_id="t1")
    session.add_message(
        "assistant",
        [{"type": "text", "text": "Hello from Koraku."}],
        model="test",
        stop_reason="end_turn",
    )
    assert extract_last_assistant_text(session) == "Hello from Koraku."
