"""Pluggable chat session storage (memory or Redis)."""
from __future__ import annotations

import json
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import timedelta

from koraku.core import redis_client
from koraku.core.config import get_settings, settings
from koraku.core.models import SessionState, as_utc, utcnow
from koraku.core.tenant import effective_tenant_org_id

log = logging.getLogger(__name__)

SessionStoreBackend = str  # "memory" | "redis"


class SessionStore(ABC):
    @abstractmethod
    def get(self, session_id: str) -> SessionState | None: ...

    @abstractmethod
    def save(self, session: SessionState) -> None: ...

    @abstractmethod
    def delete(self, session_id: str) -> None: ...

    @abstractmethod
    def count(self) -> int: ...

    def prune(self) -> None:
        """Optional maintenance hook (memory store evicts idle sessions)."""

    def get_or_create(
        self,
        raw_session_id: str | None,
        *,
        owner_sub: str | None = None,
        owner_org_id: str | None = None,
    ) -> SessionState:
        self.prune()
        rs = (raw_session_id or "").strip()
        if rs:
            rs = rs[:255]
            try:
                uuid.UUID(rs)
            except ValueError:
                rs = ""
            if rs:
                existing = self.get(rs)
                if existing is not None:
                    if existing.owner_sub != owner_sub or existing.owner_org_id != owner_org_id:
                        self.delete(rs)
                    elif utcnow() - as_utc(existing.updated_at) <= timedelta(
                        hours=float(settings.session_ttl_hours)
                    ):
                        existing.touch()
                        self.save(existing)
                        return existing
                    else:
                        self.delete(rs)
                return self._create(rs, owner_sub=owner_sub, owner_org_id=owner_org_id)
        return self._create(owner_sub=owner_sub, owner_org_id=owner_org_id)

    def _create(
        self,
        session_id: str | None = None,
        *,
        owner_sub: str | None = None,
        owner_org_id: str | None = None,
    ) -> SessionState:
        sid = (session_id or "").strip()
        if sid:
            sid = sid[:255]
        sid = sid or str(uuid.uuid4())
        session = SessionState(session_id=sid, owner_sub=owner_sub, owner_org_id=owner_org_id)
        self.save(session)
        return session


class MemorySessionStore(SessionStore):
    def __init__(self) -> None:
        self.sessions: dict[str, SessionState] = {}

    def get(self, session_id: str) -> SessionState | None:
        return self.sessions.get(session_id)

    def save(self, session: SessionState) -> None:
        self.sessions[session.session_id] = session

    def delete(self, session_id: str) -> None:
        self.sessions.pop(session_id, None)

    def count(self) -> int:
        return len(self.sessions)

    def prune(self) -> None:
        now = utcnow()
        ttl = timedelta(hours=float(settings.session_ttl_hours))
        for sid in list(self.sessions.keys()):
            s = self.sessions.get(sid)
            if s is None:
                continue
            if now - as_utc(s.updated_at) > ttl:
                del self.sessions[sid]
        max_n = int(settings.session_store_max)
        while len(self.sessions) > max_n:
            oldest = min(self.sessions.keys(), key=lambda k: as_utc(self.sessions[k].updated_at))
            del self.sessions[oldest]


class RedisSessionStore(SessionStore):
    """Redis session store (``REDIS_URL``) for multi-worker chat continuity."""

    def _ttl_seconds(self) -> int:
        return max(60, int(float(settings.session_ttl_hours) * 3600))

    def _key(self, session_id: str) -> str:
        org = effective_tenant_org_id()
        if org:
            return f"koraku:{org}:session:{session_id}"
        return f"koraku:session:{session_id}"

    def get(self, session_id: str) -> SessionState | None:
        raw = redis_client.get(self._key(session_id))
        if not raw:
            return None
        try:
            payload = json.loads(str(raw))
            return SessionState.model_validate(payload)
        except (json.JSONDecodeError, ValueError) as e:
            log.warning("Invalid session payload for %s: %s", session_id, e)
            self.delete(session_id)
            return None

    def save(self, session: SessionState) -> None:
        payload = session.model_dump(mode="json")
        encoded = json.dumps(payload, ensure_ascii=False)
        ok = redis_client.setex(self._key(session.session_id), encoded, self._ttl_seconds())
        if not ok:
            log.warning("Failed to persist session %s to Redis", session.session_id)

    def delete(self, session_id: str) -> None:
        redis_client.delete(self._key(session_id))

    def count(self) -> int:
        return -1

    def prune(self) -> None:
        return


_store: SessionStore | None = None


def build_session_store(backend: SessionStoreBackend | None = None) -> SessionStore:
    name = (backend or settings.session_store_backend or "memory").strip().lower()
    if name == "redis":
        if not redis_client.is_configured():
            log.warning("session_store_backend=redis but REDIS_URL is unset; falling back to memory")
            return MemorySessionStore()
        if redis_client.get_client() is None:
            log.warning("REDIS_URL is set but Redis is unreachable; falling back to memory")
            return MemorySessionStore()
        return RedisSessionStore()
    return MemorySessionStore()


def get_session_store() -> SessionStore:
    global _store
    if _store is None:
        _store = build_session_store()
    return _store


def reset_session_store() -> None:
    global _store
    _store = None
    redis_client.reset_client()


def active_session_count() -> int:
    store = get_session_store()
    n = store.count()
    if n >= 0:
        return n
    if isinstance(store, MemorySessionStore):
        return len(store.sessions)
    return 0
