"""Context for **ComposioRun** so the tool handler can reach the parent agent session during a delegated turn."""
from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from koraku.agent.runtime_context import AgentRunContext
    from koraku.core.models import SessionState


@dataclass(frozen=True)
class ComposioDelegateContext:
    """Bound to one parent `_run_agent_turn` while the model may call ComposioRun."""

    agent: Any
    emit: Callable[[dict[str, Any]], None]
    session: SessionState
    workspace: str
    model: str | None
    provider: str | None
    client_timezone: str | None
    client_locale: str | None
    execution_target: str
    blaxel_sandbox_active: bool
    run_context: AgentRunContext | None
    cloud_sandbox: Any
    account_personalization: dict[str, str] | None
    run_id: str | None
    cancel_event: Any  # asyncio.Event | None


_ctx: ContextVar[ComposioDelegateContext | None] = ContextVar("koraku_composio_delegate_ctx", default=None)


def set_composio_delegate_context(ctx: ComposioDelegateContext) -> Token:
    return _ctx.set(ctx)


def reset_composio_delegate_context(token: Token | None) -> None:
    if token is not None:
        _ctx.reset(token)


def get_composio_delegate_context() -> ComposioDelegateContext | None:
    return _ctx.get()
