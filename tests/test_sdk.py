"""Embeddable SDK surface: Koraku facade, config, and custom tools."""
from __future__ import annotations

import asyncio

import pytest

from koraku import Koraku, KorakuConfig, Tool, configure, get_settings, use_settings
from koraku.core.config import Settings
from koraku.core.models import SessionState


async def _echo_handler(query: str) -> str:
    return f"Echo: {query}"


def test_public_api_exports() -> None:
    from koraku import (
        Agent,
        Koraku,
        KorakuConfig,
        SessionState,
        Settings,
        Tool,
        UnifiedLLMClient,
        configure,
        get_settings,
        use_settings,
    )

    assert Agent is not None
    assert Koraku is not None
    assert KorakuConfig is not None
    assert SessionState is not None
    assert Settings is not None
    assert Tool is not None
    assert UnifiedLLMClient is not None
    assert callable(configure)
    assert callable(get_settings)
    assert callable(use_settings)


def test_koraku_config_to_settings() -> None:
    cfg = KorakuConfig(
        llm_provider="anthropic",
        anthropic_api_key="test-key",
        max_steps=7,
        require_auth_for_chat=False,
    )
    settings = cfg.to_settings()
    assert settings.llm_provider == "anthropic"
    assert settings.anthropic_api_key == "test-key"
    assert settings.max_steps == 7
    assert settings.require_auth_for_chat is False


def test_configure_and_use_settings_are_isolated() -> None:
    baseline = get_settings()
    custom = Settings(agent_name="sdk-test-agent", max_steps=3)

    configure(custom)
    assert get_settings().agent_name == "sdk-test-agent"
    assert get_settings().max_steps == 3

    with use_settings(Settings(agent_name="scoped-agent")):
        assert get_settings().agent_name == "scoped-agent"

    assert get_settings().agent_name == "sdk-test-agent"

    configure(baseline)


def test_koraku_accepts_settings_instance() -> None:
    agent = Koraku(Settings(llm_provider="fireworks", require_auth_for_chat=False))
    assert agent.settings.llm_provider == "fireworks"


@pytest.mark.asyncio
async def test_koraku_stream_with_custom_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    """Custom tools passed to Koraku are available on the active tool list."""
    from koraku.agent import run as agent_run

    from koraku.tools.registry import tools_for_execution_target

    captured: list[str] = []

    async def fake_run(self, user_input, session, emit, **kwargs):  # type: ignore[no-untyped-def]
        run_context = kwargs.get("run_context")
        tools = tools_for_execution_target("server")
        if run_context is not None and run_context.extra_tools:
            tools = tools + list(run_context.extra_tools)
        captured.extend(t.name for t in tools)
        yield {"type": "agent.final", "data": {"text": "ok"}}

    monkeypatch.setattr(agent_run.Agent, "run", fake_run)

    echo = Tool(
        name="Echo",
        description="Echo text",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
        handler=_echo_handler,
    )
    agent = Koraku(KorakuConfig(require_auth_for_chat=False), tools=[echo])

    events = [event async for event in agent.stream("hi", session=SessionState(session_id="s1"))]
    assert captured
    assert "Echo" in captured
    assert events[-1]["type"] == "agent.final"


def test_koraku_run_collects_session(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_run(self, user_input, session, emit, **kwargs):  # type: ignore[no-untyped-def]
        session.add_message("assistant", "done")
        yield {"type": "agent.final", "data": {"text": "done"}}

    from koraku.agent import run as agent_run

    monkeypatch.setattr(agent_run.Agent, "run", fake_run)

    agent = Koraku(KorakuConfig(require_auth_for_chat=False))

    async def _run() -> SessionState:
        return await agent.run("hello")

    state = asyncio.run(_run())
    assert any(m.role == "assistant" for m in state.messages)
