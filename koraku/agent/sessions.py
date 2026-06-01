"""Chat session store (memory or Redis) shared by stream routes and health."""
from __future__ import annotations

from koraku.core.session_store import get_session_store


def create_session(
    session_id: str | None = None,
    *,
    owner_sub: str | None = None,
    owner_org_id: str | None = None,
):
    session = get_session_store()._create(
        session_id, owner_sub=owner_sub, owner_org_id=owner_org_id
    )
    return session


def prune_chat_sessions() -> None:
    get_session_store().prune()


def get_or_create_chat_session(
    raw_session_id: str | None,
    *,
    owner_sub: str | None = None,
    owner_org_id: str | None = None,
):
    return get_session_store().get_or_create(
        raw_session_id, owner_sub=owner_sub, owner_org_id=owner_org_id
    )
