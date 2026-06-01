"""Supabase chat history row trimming and mapping."""

from __future__ import annotations

import pytest

from koraku.core.models import SessionState
from koraku.integrations.supabase_chat_history import (
    client_history_rows_to_agent_messages,
    db_message_rows_to_agent_messages,
    hydrate_session_messages_from_db,
    trim_persisted_rows_for_incoming_message,
)


def test_trim_removes_placeholder_user_assistant_pair() -> None:
    rows = [
        {"role": "user", "content_json": {"text": "first"}},
        {"role": "assistant", "content_json": {"run": {"assistantMarkdown": "Done."}}},
        {"role": "user", "content_json": {"text": "second q"}},
        {
            "role": "assistant",
            "content_json": {"run": {"assistantMarkdown": "", "error": None}},
        },
    ]
    out = trim_persisted_rows_for_incoming_message(rows, "second q")
    assert len(out) == 2
    assert out[-1]["role"] == "assistant"


def test_trim_does_not_remove_distinct_repeat_text() -> None:
    rows = [
        {"role": "user", "content_json": {"text": "hi"}},
        {"role": "assistant", "content_json": {"run": {"assistantMarkdown": "Hello."}}},
    ]
    out = trim_persisted_rows_for_incoming_message(rows, "hi")
    assert len(out) == 2


def test_db_rows_to_agent_messages() -> None:
    msgs = db_message_rows_to_agent_messages(
        [
            {"role": "user", "content_json": {"text": "Q?"}},
            {"role": "assistant", "content_json": {"run": {"assistantMarkdown": "**A**"}}},
        ],
    )
    assert len(msgs) == 2
    assert msgs[0].role == "user"
    assert msgs[1].role == "assistant"


def test_db_rows_skip_empty_assistant_placeholder() -> None:
    msgs = db_message_rows_to_agent_messages(
        [
            {"role": "user", "content_json": {"text": "Q?"}},
            {"role": "assistant", "content_json": {"run": {"assistantMarkdown": "", "error": None}}},
            {"role": "user", "content_json": {"text": "??"}},
        ],
    )
    assert len(msgs) == 2
    assert [m.role for m in msgs] == ["user", "user"]
    assert msgs[1].content[0]["text"] == "??"  # type: ignore[index]


def test_db_rows_keep_assistant_error_as_text() -> None:
    msgs = db_message_rows_to_agent_messages(
        [
            {"role": "user", "content_json": {"text": "Q?"}},
            {"role": "assistant", "content_json": {"run": {"assistantMarkdown": "", "error": "boom"}}},
        ],
    )
    assert len(msgs) == 2
    assert msgs[1].role == "assistant"
    assert "boom" in msgs[1].content[0]["text"]  # type: ignore[index]


def test_client_history_rows_to_agent_messages_visible_text_only() -> None:
    msgs = client_history_rows_to_agent_messages(
        [
            {"role": "user", "text": "fetch latest news"},
            {"role": "assistant", "text": "Saved latest_news_2026-04-25.md"},
            {"role": "assistant", "text": ""},
            {"role": "tool", "text": "ignored"},
        ],
    )
    assert len(msgs) == 2
    assert msgs[0].role == "user"
    assert msgs[1].role == "assistant"
    assert "latest_news_2026-04-25.md" in msgs[1].content[0]["text"]  # type: ignore[index]


@pytest.mark.asyncio
async def test_hydrate_uses_client_history_when_auth_missing() -> None:
    session = SessionState(session_id="94994f06-10d1-47d4-ad13-e98b0baf06d2")
    report = await hydrate_session_messages_from_db(
        session,
        incoming_user_text="send sarthak this news",
        auth_sub=None,
        client_history=[
            {"role": "user", "text": "fetch latest news and save it as md"},
            {"role": "assistant", "text": "Saved latest_news_2026-04-25.md"},
        ],
    )
    assert report.source == "client"
    assert report.reason == "missing_auth"
    assert report.auth_present is False
    assert report.messages_loaded == 2
    assert len(session.messages) == 2
    assert "latest_news_2026-04-25.md" in session.messages[1].content[0]["text"]  # type: ignore[index]
