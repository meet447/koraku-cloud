"""ContextVar binding the active Blaxel ``SandboxInstance`` for tool handlers."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any, Iterator

_active_blaxel_sandbox: ContextVar[Any | None] = ContextVar("koraku_blaxel_sandbox", default=None)
_active_blaxel_session_root: ContextVar[str | None] = ContextVar("koraku_blaxel_session_root", default=None)


def get_active_blaxel_sandbox() -> Any | None:
    return _active_blaxel_sandbox.get()


def get_active_blaxel_session_root() -> str | None:
    """Absolute POSIX session folder inside the VM (Read/Write cwd for this chat)."""
    return _active_blaxel_session_root.get()


def bind_blaxel_sandbox(sandbox: Any, session_root: str) -> tuple[Token[Any | None], Token[str | None]]:
    """Attach a sandbox for the current async context (e.g. lazy provisioning mid-turn)."""
    t_sb: Token[Any | None] = _active_blaxel_sandbox.set(sandbox)
    t_root: Token[str | None] = _active_blaxel_session_root.set(session_root.strip())
    return t_sb, t_root


@contextmanager
def blaxel_sandbox_scope(sandbox: Any | None) -> Iterator[None]:
    if sandbox is None:
        yield
        return
    token: Token[Any | None] = _active_blaxel_sandbox.set(sandbox)
    try:
        yield
    finally:
        _active_blaxel_sandbox.reset(token)


@contextmanager
def blaxel_session_workspace_scope(session_root: str | None) -> Iterator[None]:
    if not (session_root or "").strip():
        yield
        return
    token: Token[str | None] = _active_blaxel_session_root.set(session_root.strip())
    try:
        yield
    finally:
        _active_blaxel_session_root.reset(token)
