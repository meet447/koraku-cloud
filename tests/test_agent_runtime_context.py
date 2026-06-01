"""Agent run context: sandbox-only chat execution."""
from __future__ import annotations

import os

import pytest
from types import SimpleNamespace

from koraku.agent.runtime_context import AgentRunContext, resolve_agent_workspace, resolve_execution_target
from koraku.integrations.blaxel_runtime import session_workspace_root_posix, user_sandbox_name
from koraku.integrations.cloud_user import reset_cloud_user_id, set_cloud_user_id
from koraku.tools.registry import bash_tool, tools_for_execution_target


def test_user_sandbox_name_sanitizes_user_id() -> None:
    assert user_sandbox_name("org/user") == "koraku-user-orguser"
    assert user_sandbox_name("a_b_c").startswith("koraku-user-")


def test_session_workspace_contains_user_and_session() -> None:
    s = SimpleNamespace(blaxel_sandbox_workdir="/tmp")
    sid = "550e8400-e29b-41d4-a716-446655440000"
    p = session_workspace_root_posix("org-1/user-2", sid, s)
    assert p == f"/tmp/koraku/users/org-1-user-2/sessions/{sid}"


def test_resolve_agent_workspace_explicit_wins() -> None:
    ctx = AgentRunContext(workspace_root="/tmp/from-context")
    assert resolve_agent_workspace("/tmp/explicit", ctx) == os.path.abspath("/tmp/explicit")


def test_resolve_agent_workspace_from_context() -> None:
    ctx = AgentRunContext(workspace_root="/tmp/ws")
    assert resolve_agent_workspace(None, ctx) == os.path.abspath("/tmp/ws")


def test_resolve_execution_target_is_always_cloud() -> None:
    assert resolve_execution_target(AgentRunContext()) == "cloud"
    assert resolve_execution_target(None) == "cloud"


def test_tools_for_cloud_sandbox() -> None:
    cloud_names = {t.name for t in tools_for_execution_target("cloud")}
    assert "Bash" not in cloud_names
    cloud_with_blaxel = {t.name for t in tools_for_execution_target("cloud", blaxel_sandbox_active=True)}
    assert bash_tool.name in cloud_with_blaxel


def test_stream_chat_body_defaults_to_cloud_only() -> None:
    from koraku.api.chat_routes import StreamChatBody

    assert StreamChatBody(msg="hello").model_dump().get("execution_target") is None


def test_stream_chat_body_accepts_client_history() -> None:
    from koraku.api.chat_routes import StreamChatBody

    b = StreamChatBody(
        msg="send sarthak this news",
        client_history=[
            {"role": "user", "text": "fetch latest news and save it as md"},
            {"role": "assistant", "text": "Saved latest_news_2026-04-25.md"},
        ],
    )
    assert len(b.client_history) == 2
    assert b.client_history[1].role == "assistant"


def test_stream_cloud_blaxel_blocked_sse_has_completed_and_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    import koraku.api.chat_routes as chat_routes
    from koraku.server import app

    monkeypatch.setattr(chat_routes.settings, "require_auth_for_chat", False, raising=False)
    monkeypatch.setattr(chat_routes, "cloud_blaxel_block_reason", lambda _s: "blocked-for-test")
    client = TestClient(app)
    with client.stream("POST", "/stream", json={"msg": "hi"}) as r:
        assert r.status_code == 200
        body = "".join(r.iter_text())
    assert "koraku.started" in body
    assert "koraku.completed" in body
    assert "blocked-for-test" in body
    assert "event: done" in body


def test_effective_cloud_user_id_requires_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    from koraku.integrations.cloud_user import effective_cloud_user_id

    with pytest.raises(RuntimeError, match="Authenticated"):
        effective_cloud_user_id()

    tok = set_cloud_user_id("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    try:
        assert effective_cloud_user_id() == "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    finally:
        reset_cloud_user_id(tok)
