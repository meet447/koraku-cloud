"""Per-request context for tools that need session state (e.g. TodoWrite)."""
from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from koraku.core.models import SessionState

_active_session: ContextVar["SessionState | None"] = ContextVar("koraku_active_session", default=None)


def get_active_session() -> "SessionState | None":
    return _active_session.get()


def set_active_session(session: "SessionState | None") -> None:
    _active_session.set(session)
