"""Active external channel for the current agent turn (ContextVar)."""
from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Awaitable, Callable


@dataclass(frozen=True)
class ActiveChannel:
    kind: str
    outbound_phone: str
    thread_id: str
    user_id: str
    org_id: str


_active: ContextVar[ActiveChannel | None] = ContextVar("koraku_active_channel", default=None)
_on_send: ContextVar[Callable[[str], Awaitable[None]] | None] = ContextVar(
    "koraku_channel_on_send",
    default=None,
)


def set_active_channel(
    channel: ActiveChannel | None,
    *,
    on_send: Callable[[str], Awaitable[None]] | None = None,
) -> tuple[Token, Token | None]:
    t1 = _active.set(channel)
    t2 = _on_send.set(on_send) if on_send is not None else None
    return t1, t2


def reset_active_channel(t1: Token, t2: Token | None) -> None:
    _active.reset(t1)
    if t2 is not None:
        _on_send.reset(t2)


def get_active_channel() -> ActiveChannel | None:
    return _active.get()


async def deliver_channel_message(text: str) -> bool:
    fn = _on_send.get()
    if fn is None:
        return False
    await fn(text)
    return True
