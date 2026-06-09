"""Resolve active memory backend(s) from settings."""
from __future__ import annotations

from typing import TYPE_CHECKING

from koraku.core.config import Settings, get_settings, is_cloud_configured
from koraku.plugins.memory.filesystem import FilesystemLearnedMemoryBackend
from koraku.plugins.memory.supermemory import SupermemoryBackend

if TYPE_CHECKING:
    from koraku.plugins.memory.base import MemoryBackend

_cached_backend: MemoryBackend | None = None
_cached_key: str | None = None


class CompositeMemoryBackend:
    """Filesystem learned memory + optional Supermemory when configured."""

    name = "composite"

    def __init__(self) -> None:
        self._fs = FilesystemLearnedMemoryBackend()
        self._sm = SupermemoryBackend()

    def supports_agent_tools(self) -> bool:
        return self._fs.supports_agent_tools() or self._sm.supports_agent_tools()

    def agent_tools(self) -> list:
        from koraku.tools.tool_def import Tool

        tools: list[Tool] = []
        seen: set[str] = set()
        for backend in (self._sm, self._fs):
            for t in backend.agent_tools():
                if t.name in seen:
                    continue
                seen.add(t.name)
                tools.append(t)
        return tools

    async def prefetch_learned(self, user_input: str, *, workspace: str) -> str:
        parts: list[str] = []
        sm = await self._sm.prefetch_learned(user_input, workspace=workspace)
        if sm.strip():
            parts.append(sm.strip())
        fs = await self._fs.prefetch_learned(user_input, workspace=workspace)
        if fs.strip():
            parts.append(fs.strip())
        return "\n\n".join(parts)


def _resolve_backend_name(settings: Settings) -> str:
    raw = (settings.memory_backend or "auto").strip().lower()
    if raw != "auto":
        return raw
    if is_cloud_configured():
        return "supermemory"
    return "filesystem"


def get_memory_backend(settings: Settings | None = None) -> MemoryBackend:
    global _cached_backend, _cached_key
    s = settings if settings is not None else get_settings()
    mode = "cloud" if is_cloud_configured() else "sdk"
    key = f"{mode}:{s.memory_backend}:{s.supermemory_api_key}"
    if _cached_backend is not None and _cached_key == key:
        return _cached_backend
    name = _resolve_backend_name(s)
    if name == "supermemory":
        backend: MemoryBackend = SupermemoryBackend()
    elif name == "composite":
        backend = CompositeMemoryBackend()
    else:
        backend = FilesystemLearnedMemoryBackend()
    _cached_backend = backend
    _cached_key = key
    return backend


def reset_memory_backend_cache() -> None:
    global _cached_backend, _cached_key
    _cached_backend = None
    _cached_key = None


def memory_agent_tools(settings: Settings | None = None) -> list:
    backend = get_memory_backend(settings)
    if not backend.supports_agent_tools():
        return []
    return list(backend.agent_tools())


async def prefetch_learned_memory_volatile(user_input: str, *, workspace: str) -> str:
    backend = get_memory_backend()
    return await backend.prefetch_learned(user_input, workspace=workspace)
