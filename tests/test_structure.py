"""Quick validation that the agent structure loads correctly."""
import asyncio


def test_tool_result_policy():
    from koraku.tools.policy import tool_stdout_indicates_error

    assert tool_stdout_indicates_error("", tool_name="WebFetch") is True
    assert tool_stdout_indicates_error("Error: timeout", tool_name="Bash") is True
    assert tool_stdout_indicates_error("Error: Fetch failed: x", tool_name="WebFetch") is True
    assert tool_stdout_indicates_error("No matches.", tool_name="Grep") is False
    assert tool_stdout_indicates_error('[{"url": "https://x"}]', tool_name="WebSearch") is False


def test_openai_native_tool_call_merge():
    from koraku.llm import _accumulate_openai_tool_call_deltas, _tool_call_slots_to_blocks

    slots: dict[int, dict[str, str]] = {}
    _accumulate_openai_tool_call_deltas(
        slots,
        [
            {
                "index": 0,
                "id": "call_1",
                "type": "function",
                "function": {"name": "Glob", "arguments": ""},
            },
        ],
    )
    _accumulate_openai_tool_call_deltas(
        slots,
        [{"index": 0, "function": {"arguments": "{\"pattern\":"}}],
    )
    _accumulate_openai_tool_call_deltas(
        slots,
        [{"index": 0, "function": {"arguments": " \"*.py\"}"}}],
    )
    blocks = _tool_call_slots_to_blocks(slots)
    assert len(blocks) == 1
    assert blocks[0]["type"] == "tool_use"
    assert blocks[0]["name"] == "Glob"
    assert blocks[0]["input"]["pattern"] == "*.py"


def test_imports():
    from koraku.core.config import settings
    from koraku.tools import AVAILABLE_TOOLS, get_tool, get_tool_schemas
    from koraku.llm import UnifiedLLMClient
    from koraku.agent import Agent
    from koraku_cloud.app import app

    assert app is not None
    assert UnifiedLLMClient is not None
    assert Agent is not None
    assert settings.agent_name
    assert len(AVAILABLE_TOOLS) > 0
    wf = get_tool("WebFetch")
    if wf is not None:
        assert get_tool("WebPage") is wf
    assert len(get_tool_schemas()) > 0


async def _run_tool_smoke_async():
    from koraku.agent.runtime_context import bind_execution_target, reset_execution_target
    from koraku.tools import bash_tool, glob_tool, grep_tool, read_tool
    from koraku.workspace.agent_workspace import agent_workspace_scope

    tok = bind_execution_target("local")
    try:
        with agent_workspace_scope("."):
            result = await bash_tool.run(command="echo 'hello from agent'")
            assert "hello from agent" in result, f"Bash failed: {result}"

            result = await glob_tool.run(pattern="*.md")
            assert "README.md" in result, f"Glob failed: {result}"

            result = await grep_tool.run(pattern="class Agent", include="*.py")
            assert "koraku/agent/run.py" in result, f"Grep failed: {result}"

            result = await read_tool.run(file_path="README.md")
            assert "Koraku" in result, f"Read failed: {result}"
    finally:
        reset_execution_target(tok)


def test_tools():
    asyncio.run(_run_tool_smoke_async())


def test_server_routes(monkeypatch):
    from fastapi.testclient import TestClient
    from koraku_cloud.app import app
    import koraku.api.chat_routes as chat_routes

    monkeypatch.setattr(chat_routes.settings, "require_auth_for_chat", False, raising=False)

    client = TestClient(app)

    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("service")
    assert body.get("health") == "/health"

    resp = client.post("/stream", json={})
    assert resp.status_code == 422

    from koraku.server_sdk import _MODE as server_mode

    if server_mode == "unconfigured":
        resp = client.post("/stream", json={"msg": "hi"})
        assert resp.status_code == 200
        ct = resp.headers.get("content-type") or ""
        assert "text/event-stream" in ct
        assert "koraku.started" in resp.text or "data:" in resp.text


