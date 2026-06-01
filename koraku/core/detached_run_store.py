"""Detached agent run buffers: in-process (single worker) or Redis (multi-worker)."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from koraku.core import redis_async
from koraku.core.config import settings

log = logging.getLogger(__name__)

_DETACHED_GC_SEC = float((os.environ.get("KORAKU_DETACHED_RUN_GC_SECONDS") or "600").strip() or "600")
_MAX_CHUNKS_PER_RUN = 12_000
_SUBSCRIBER_QUEUE_MAX = max(16, int(settings.detached_run_subscriber_queue_max))
_SENTINEL: object = object()
_DONE_CHANNEL_MSG = "__koraku_detached_done__"


def detached_gc_seconds() -> float:
    return _DETACHED_GC_SEC


def subscriber_queue_max() -> int:
    return _SUBSCRIBER_QUEUE_MAX


def _run_prefix(owner_org_id: str | None, run_id: str) -> str:
    org = (owner_org_id or "").strip()
    if org:
        return f"koraku:{org}:run:{run_id}"
    return f"koraku:run:{run_id}"


class DetachedRunBuffer(ABC):
    owner_sub: str | None
    owner_org_id: str | None

    @abstractmethod
    def allows(self, auth_sub: str | None, auth_org_id: str | None = None) -> bool: ...

    @abstractmethod
    async def append(self, raw_chunk: str) -> None: ...

    @abstractmethod
    async def finish(self) -> None: ...

    @abstractmethod
    async def status_snapshot(self) -> dict[str, Any]: ...

    @abstractmethod
    async def subscribe(self, after: int) -> AsyncIterator[str]: ...


class MemoryRunBuffer(DetachedRunBuffer):
    __slots__ = (
        "owner_sub",
        "owner_org_id",
        "chunks",
        "next_seq",
        "done",
        "lock",
        "subscribers",
    )

    def __init__(self, owner_sub: str | None, owner_org_id: str | None = None) -> None:
        self.owner_sub = owner_sub
        self.owner_org_id = owner_org_id
        self.chunks: list[tuple[int, str]] = []
        self.next_seq = 0
        self.done = False
        self.lock = asyncio.Lock()
        self.subscribers: list[asyncio.Queue[Any]] = []

    def allows(self, auth_sub: str | None, auth_org_id: str | None = None) -> bool:
        if self.owner_sub is None:
            return True
        if auth_sub != self.owner_sub:
            return False
        if self.owner_org_id and auth_org_id != self.owner_org_id:
            return False
        return True

    async def append(self, raw_chunk: str) -> None:
        async with self.lock:
            if self.done:
                return
            seq = self.next_seq
            self.next_seq += 1
            if raw_chunk.startswith("id: "):
                wrapped = raw_chunk
            else:
                wrapped = f"id: {seq}\n{raw_chunk}"
            self.chunks.append((seq, wrapped))
            if len(self.chunks) > _MAX_CHUNKS_PER_RUN:
                self.chunks.pop(0)
            subs = list(self.subscribers)
        slow_subscribers: list[asyncio.Queue[Any]] = []
        for q in subs:
            try:
                q.put_nowait(wrapped)
            except asyncio.QueueFull:
                slow_subscribers.append(q)
                try:
                    q.put_nowait(_SENTINEL)
                except asyncio.QueueFull:
                    pass
        if slow_subscribers:
            async with self.lock:
                for q in slow_subscribers:
                    try:
                        self.subscribers.remove(q)
                    except ValueError:
                        pass

    async def finish(self) -> None:
        async with self.lock:
            self.done = True
            subs = list(self.subscribers)
            self.subscribers.clear()
        for q in subs:
            try:
                await q.put(_SENTINEL)
            except Exception:
                pass

    async def status_snapshot(self) -> dict[str, Any]:
        async with self.lock:
            done = self.done
            nchunks = len(self.chunks)
            last_id = self.chunks[-1][0] if self.chunks else -1
        return {
            "state": "completed" if done else "running",
            "last_event_id": last_id,
            "buffered_chunks": nchunks,
        }

    async def subscribe(self, after: int) -> AsyncIterator[str]:
        q: asyncio.Queue[Any] = asyncio.Queue(maxsize=_SUBSCRIBER_QUEUE_MAX)
        try:
            async with self.lock:
                is_done = self.done
                if not is_done:
                    self.subscribers.append(q)
                replay = [(s, w) for s, w in self.chunks if s > after]
            for _, w in replay:
                yield w
            if is_done:
                return
            while True:
                item = await q.get()
                if item is _SENTINEL:
                    break
                yield item
        finally:
            async with self.lock:
                try:
                    self.subscribers.remove(q)
                except ValueError:
                    pass


class RedisRunBuffer(DetachedRunBuffer):
    """Chunk list + pub/sub so any API worker can subscribe to a run."""

    __slots__ = ("run_id", "owner_sub", "owner_org_id", "_prefix")

    def __init__(
        self,
        run_id: str,
        owner_sub: str | None,
        owner_org_id: str | None,
    ) -> None:
        self.run_id = run_id
        self.owner_sub = owner_sub
        self.owner_org_id = owner_org_id
        self._prefix = _run_prefix(owner_org_id, run_id)

    def _meta_key(self) -> str:
        return f"{self._prefix}:meta"

    def _chunks_key(self) -> str:
        return f"{self._prefix}:chunks"

    def _channel_key(self) -> str:
        return f"{self._prefix}:live"

    def allows(self, auth_sub: str | None, auth_org_id: str | None = None) -> bool:
        if self.owner_sub is None:
            return True
        if auth_sub != self.owner_sub:
            return False
        if self.owner_org_id and auth_org_id != self.owner_org_id:
            return False
        return True

    async def _client(self) -> Any:
        client = await redis_async.get_client()
        if client is None:
            raise RuntimeError("Redis client unavailable")
        return client

    async def _load_meta(self) -> dict[str, Any] | None:
        client = await self._client()
        raw = await client.get(self._meta_key())
        if not raw:
            return None
        try:
            return json.loads(str(raw))
        except json.JSONDecodeError:
            return None

    async def append(self, raw_chunk: str) -> None:
        meta = await self._load_meta()
        if meta is None or meta.get("done"):
            return
        client = await self._client()
        seq = int(await client.incr(f"{self._prefix}:seq")) - 1
        if raw_chunk.startswith("id: "):
            wrapped = raw_chunk
        else:
            wrapped = f"id: {seq}\n{raw_chunk}"
        entry = json.dumps({"seq": seq, "data": wrapped}, ensure_ascii=False)
        pipe = client.pipeline()
        pipe.rpush(self._chunks_key(), entry)
        pipe.ltrim(self._chunks_key(), -_MAX_CHUNKS_PER_RUN, -1)
        pipe.expire(self._chunks_key(), int(_DETACHED_GC_SEC))
        pipe.expire(self._meta_key(), int(_DETACHED_GC_SEC))
        pipe.publish(self._channel_key(), wrapped)
        await pipe.execute()
        meta["next_seq"] = seq + 1
        meta["last_event_id"] = seq
        await client.set(
            self._meta_key(),
            json.dumps(meta, ensure_ascii=False),
            ex=int(_DETACHED_GC_SEC),
        )

    async def finish(self) -> None:
        client = await self._client()
        meta = await self._load_meta()
        if meta is not None:
            meta["done"] = True
            await client.set(
                self._meta_key(),
                json.dumps(meta, ensure_ascii=False),
                ex=int(_DETACHED_GC_SEC),
            )
        ttl = int(_DETACHED_GC_SEC)
        await client.expire(self._chunks_key(), ttl)
        await client.publish(self._channel_key(), _DONE_CHANNEL_MSG)

    async def status_snapshot(self) -> dict[str, Any]:
        meta = await self._load_meta()
        if meta is None:
            return {
                "state": "not_found",
                "last_event_id": -1,
                "buffered_chunks": 0,
            }
        done = bool(meta.get("done"))
        client = await self._client()
        nchunks = int(await client.llen(self._chunks_key()) or 0)
        last_id = int(meta.get("last_event_id", -1))
        return {
            "state": "completed" if done else "running",
            "last_event_id": last_id,
            "buffered_chunks": nchunks,
        }

    async def _replay(self, after: int) -> list[str]:
        client = await self._client()
        raw_list = await client.lrange(self._chunks_key(), 0, -1)
        out: list[str] = []
        for raw in raw_list:
            try:
                item = json.loads(str(raw))
            except json.JSONDecodeError:
                continue
            seq = int(item.get("seq", -1))
            if seq > after:
                out.append(str(item.get("data", "")))
        return out

    async def subscribe(self, after: int) -> AsyncIterator[str]:
        for w in await self._replay(after):
            yield w
        meta = await self._load_meta()
        if meta is None or meta.get("done"):
            return
        client = await self._client()
        pubsub = client.pubsub()
        await pubsub.subscribe(self._channel_key())
        try:
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                payload = str(message.get("data", ""))
                if payload == _DONE_CHANNEL_MSG:
                    break
                yield payload
        finally:
            try:
                await pubsub.unsubscribe(self._channel_key())
            except Exception:
                pass
            try:
                await pubsub.aclose()
            except Exception:
                pass


class DetachedRunStore(ABC):
    @abstractmethod
    async def register(
        self,
        run_id: str,
        *,
        owner_sub: str | None,
        owner_org_id: str | None,
    ) -> DetachedRunBuffer: ...

    @abstractmethod
    async def get(
        self,
        run_id: str,
        *,
        owner_org_id: str | None = None,
    ) -> DetachedRunBuffer | None: ...

    @abstractmethod
    async def drop(
        self,
        run_id: str,
        *,
        owner_org_id: str | None = None,
    ) -> None: ...


class MemoryDetachedRunStore(DetachedRunStore):
    def __init__(self) -> None:
        self._buffers: dict[str, MemoryRunBuffer] = {}
        self._lock = asyncio.Lock()

    async def register(
        self,
        run_id: str,
        *,
        owner_sub: str | None,
        owner_org_id: str | None,
    ) -> DetachedRunBuffer:
        buf = MemoryRunBuffer(owner_sub=owner_sub, owner_org_id=owner_org_id)
        async with self._lock:
            self._buffers[run_id] = buf
        return buf

    async def get(
        self,
        run_id: str,
        *,
        owner_org_id: str | None = None,
    ) -> DetachedRunBuffer | None:
        _ = owner_org_id
        async with self._lock:
            return self._buffers.get(run_id)

    async def drop(
        self,
        run_id: str,
        *,
        owner_org_id: str | None = None,
    ) -> None:
        _ = owner_org_id
        async with self._lock:
            self._buffers.pop(run_id, None)


class RedisDetachedRunStore(DetachedRunStore):
    async def register(
        self,
        run_id: str,
        *,
        owner_sub: str | None,
        owner_org_id: str | None,
    ) -> DetachedRunBuffer:
        client = await redis_async.get_client()
        if client is None:
            raise RuntimeError("Redis unavailable")
        buf = RedisRunBuffer(run_id, owner_sub, owner_org_id)
        meta = {
            "owner_sub": owner_sub,
            "owner_org_id": owner_org_id,
            "done": False,
            "next_seq": 0,
            "last_event_id": -1,
        }
        ttl = int(_DETACHED_GC_SEC)
        await client.set(
            buf._meta_key(),
            json.dumps(meta, ensure_ascii=False),
            ex=ttl,
        )
        return buf

    async def get(
        self,
        run_id: str,
        *,
        owner_org_id: str | None = None,
    ) -> DetachedRunBuffer | None:
        client = await redis_async.get_client()
        if client is None:
            return None
        org_candidates: list[str | None] = []
        if owner_org_id and str(owner_org_id).strip():
            org_candidates.append(str(owner_org_id).strip())
        org_candidates.append(None)
        seen: set[str | None] = set()
        for org in org_candidates:
            if org in seen:
                continue
            seen.add(org)
            buf = RedisRunBuffer(run_id, None, org)
            raw = await client.get(buf._meta_key())
            if not raw:
                continue
            try:
                meta = json.loads(str(raw))
            except json.JSONDecodeError:
                continue
            return RedisRunBuffer(
                run_id,
                meta.get("owner_sub"),
                meta.get("owner_org_id"),
            )
        return None

    async def drop(
        self,
        run_id: str,
        *,
        owner_org_id: str | None = None,
    ) -> None:
        buf = await self.get(run_id, owner_org_id=owner_org_id)
        if buf is None:
            return
        client = await redis_async.get_client()
        if client is None:
            return
        await client.delete(
            buf._meta_key(),
            buf._chunks_key(),
            f"{buf._prefix}:seq",
        )


_store: DetachedRunStore | None = None


def build_detached_run_store(backend: str | None = None) -> DetachedRunStore:
    from koraku.core import redis_client

    name = (backend or settings.detached_run_store_backend or "auto").strip().lower()
    if name == "redis":
        if not redis_client.is_configured():
            log.warning("detached_run_store_backend=redis but REDIS_URL is unset; using memory")
            return MemoryDetachedRunStore()
        if redis_client.get_client() is None:
            log.warning("REDIS_URL is set but Redis is unreachable; detached runs use memory")
            return MemoryDetachedRunStore()
        return RedisDetachedRunStore()
    if name == "memory":
        return MemoryDetachedRunStore()
    # auto
    if redis_client.is_configured() and redis_client.get_client() is not None:
        return RedisDetachedRunStore()
    return MemoryDetachedRunStore()


def get_detached_run_store() -> DetachedRunStore:
    global _store
    if _store is None:
        _store = build_detached_run_store()
    return _store


def reset_detached_run_store() -> None:
    global _store
    _store = None
    redis_async.reset_client()
