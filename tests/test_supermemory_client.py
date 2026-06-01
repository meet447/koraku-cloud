"""Supermemory client helpers (mocked — no live API)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from koraku.core.config import Settings, configure
from koraku.core.models import SessionState
from koraku.integrations import supermemory_client as sm


@pytest.fixture(autouse=True)
def _reset_supermemory_client():
    sm._CLIENT = None
    yield
    sm._CLIENT = None


def test_container_tag_scopes_org_and_user() -> None:
    assert sm.container_tag("user-1", "org-a").startswith("koraku-")
    assert "org-a" in sm.container_tag("user-1", "org-a") or "org" in sm.container_tag("user-1", "org-a")


def test_supermemory_not_configured_without_key() -> None:
    configure(Settings(supermemory_api_key=""))
    assert sm.supermemory_configured() is False
    assert sm.fetch_learned_context_sync("u1") == ""


def test_fetch_learned_context_formats_profile() -> None:
    configure(Settings(supermemory_api_key="test-key"))
    mock_client = MagicMock()
    mock_client.profile.return_value = SimpleNamespace(
        profile=SimpleNamespace(static=["Likes dark mode"], dynamic=["Working on Koraku"]),
        search_results=SimpleNamespace(results=[{"memory": "Prefers concise replies"}]),
    )
    with patch.object(sm, "_client", return_value=mock_client):
        out = sm.fetch_learned_context_sync("user-1", org_id="org-1", query="hello")
    assert "Learned memory" in out
    assert "dark mode" in out
    mock_client.profile.assert_called_once()


def test_extract_last_assistant_text() -> None:
    session = SessionState(session_id="s1")
    session.add_message("user", "hi")
    session.add_message(
        "assistant",
        [{"type": "text", "text": "Hello there"}],
        stop_reason="end_turn",
    )
    assert sm.extract_last_assistant_text(session) == "Hello there"


def test_save_memory_omits_custom_id_when_unset() -> None:
    configure(Settings(supermemory_api_key="test-key"))
    mock_client = MagicMock()
    with patch.object(sm, "_client", return_value=mock_client):
        result = sm.save_memory_sync("user-1", "User is starting their 4th year in June.")
    assert result == "Saved to long-term memory."
    kwargs = mock_client.add.call_args.kwargs
    assert "custom_id" not in kwargs


def test_ingest_chat_turn_calls_add() -> None:
    configure(Settings(supermemory_api_key="test-key"))
    mock_client = MagicMock()
    with patch.object(sm, "_client", return_value=mock_client):
        sm.ingest_chat_turn_sync(
            "user-1",
            user_text="remember my dog is Max",
            assistant_text="Got it.",
            org_id="org-1",
            session_id="sess-1",
            run_id="run-1",
        )
    mock_client.add.assert_called_once()
    kwargs = mock_client.add.call_args.kwargs
    assert "user:" in kwargs["content"]
    assert kwargs["container_tag"].startswith("koraku-")
