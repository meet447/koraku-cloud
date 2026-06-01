"""Embeddable Koraku SDK facade for in-process agent runs."""
from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Any

from koraku.agent import Agent
from koraku.agent.runtime_context import AgentRunContext, ExecutionTarget
from koraku.core.config import Settings, configure, use_settings
from koraku.core.models import SessionState
from koraku.tools.tool_def import Tool

__all__ = ["Koraku", "KorakuConfig"]


@dataclass
class KorakuConfig:
    """Embeddable configuration for in-process Koraku agents."""

    llm_provider: str = "fireworks"
    fireworks_api_key: str = ""
    fireworks_model: str = "accounts/fireworks/models/kimi-k2p6"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    llm_openai_compat_ids: str = ""
    max_steps: int = 15
    max_tokens: int = 4096
    temperature: float = 0.5
    workspace: str | None = None
    execution_target: ExecutionTarget = "cloud"
    composio_api_key: str = ""
    composio_subagent_mode: bool = True
    require_auth_for_chat: bool = False
    enable_bash: bool = True
    enable_web_search: bool = True
    enable_file_ops: bool = True

    def to_settings(self) -> Settings:
        return Settings(
            llm_provider=self.llm_provider,
            fireworks_api_key=self.fireworks_api_key,
            fireworks_model=self.fireworks_model,
            anthropic_api_key=self.anthropic_api_key,
            anthropic_model=self.anthropic_model,
            llm_openai_compat_ids=self.llm_openai_compat_ids,
            max_steps=self.max_steps,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            composio_api_key=self.composio_api_key,
            composio_subagent_mode=self.composio_subagent_mode,
            require_auth_for_chat=self.require_auth_for_chat,
            enable_bash=self.enable_bash,
            enable_web_search=self.enable_web_search,
            enable_file_ops=self.enable_file_ops,
        )


class Koraku:
    """In-process embeddable Koraku agent.

    Example::

        from koraku import Koraku, KorakuConfig

        agent = Koraku(KorakuConfig(fireworks_api_key="...", llm_provider="fireworks"))
        async for event in agent.stream("Summarize this repo"):
            print(event)
    """

    def __init__(
        self,
        config: KorakuConfig | Settings | None = None,
        *,
        tools: list[Tool] | None = None,
    ) -> None:
        if isinstance(config, Settings):
            self._settings = config
        elif config is not None:
            self._settings = config.to_settings()
        else:
            self._settings = Settings()
        self._tools = tuple(tools or ())
        self._workspace = config.workspace if isinstance(config, KorakuConfig) else None

    @property
    def settings(self) -> Settings:
        return self._settings

    def configure_process(self) -> None:
        """Apply this instance's settings as the process-wide default."""
        configure(self._settings)

    def _agent(self) -> Agent:
        return Agent()

    async def stream(
        self,
        message: str,
        *,
        session: SessionState | None = None,
        session_id: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        workspace: str | None = None,
        execution_target: ExecutionTarget | None = None,
        cancel_event: asyncio.Event | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Run one agent turn and yield raw agent events (same shapes as the HTTP API internals)."""
        sid = session_id or str(uuid.uuid4())
        state = session or SessionState(session_id=sid)
        ws = workspace or self._workspace
        target: ExecutionTarget = execution_target or "cloud"
        run_context = AgentRunContext(
            workspace_root=ws,
            execution_target=target,
            extra_tools=self._tools,
        )

        def _emit(_ev: dict[str, Any]) -> None:
            return None

        with use_settings(self._settings):
            agent = self._agent()
            async for event in agent.run(
                message,
                state,
                _emit,
                workspace=ws,
                model=model,
                provider=provider,
                run_context=run_context,
                cancel_event=cancel_event,
            ):
                yield event

    async def run(
        self,
        message: str,
        *,
        on_event: Callable[[dict[str, Any]], None] | None = None,
        **kwargs: Any,
    ) -> SessionState:
        """Run one turn and return the updated session (optional event callback)."""
        sid = kwargs.pop("session_id", None) or str(uuid.uuid4())
        state = kwargs.pop("session", None) or SessionState(session_id=sid)

        async for event in self.stream(message, session=state, session_id=sid, **kwargs):
            if on_event is not None:
                on_event(event)
        return state
