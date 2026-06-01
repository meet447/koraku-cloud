"""Redis client helpers (mocked — no server required)."""
from __future__ import annotations

from koraku.core import redis_client
from koraku.core.config import Settings, use_settings


def test_increment_with_ttl(monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []

    class FakePipe:
        def incr(self, key: str) -> None:
            calls.append(("incr", key))

        def expire(self, key: str, ttl: int, nx: bool = False) -> None:
            calls.append(("expire", key, str(ttl), str(nx)))

        def execute(self) -> list[int]:
            return [3]

    class FakeClient:
        def pipeline(self) -> FakePipe:
            return FakePipe()

    redis_client.reset_client()
    with use_settings(Settings(redis_url="redis://127.0.0.1:6379/0")):
        monkeypatch.setattr(redis_client, "get_client", lambda: FakeClient())
        n = redis_client.increment_with_ttl("koraku:rl:test:1", 65)
    assert n == 3
    assert calls[0] == ("incr", "koraku:rl:test:1")
