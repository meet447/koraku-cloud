"""Personalization fetch cache."""

from __future__ import annotations

from koraku.integrations import supabase_personalization as sp


def test_fetch_personalization_uses_cache(monkeypatch) -> None:
    sp._PERSONALIZATION_CACHE.clear()
    calls = {"n": 0}

    monkeypatch.setattr(sp, "_valid_uuid", lambda _uid: True)
    monkeypatch.setattr(sp, "supabase_personalization_configured", lambda: True)
    monkeypatch.setattr(sp.settings, "personalization_cache_ttl_seconds", 300.0)

    class FakeResp:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return [{"agent_name": "A", "memory": "M", "soul": "S"}]

    class FakeClient:
        def get(self, *_args, **_kwargs):
            calls["n"] += 1
            return FakeResp()

    monkeypatch.setattr(sp, "get_http_client", lambda: FakeClient())

    uid = "11111111-1111-4111-8111-111111111111"
    oid = "33333333-3333-4333-8333-333333333333"
    first = sp.fetch_personalization_sync(uid, org_id=oid)
    second = sp.fetch_personalization_sync(uid, org_id=oid)
    assert first == {"agent_name": "A", "memory": "M", "soul": "S"}
    assert second == first
    assert calls["n"] == 1


def test_upsert_invalidates_personalization_cache(monkeypatch) -> None:
    sp._PERSONALIZATION_CACHE.clear()
    uid = "22222222-2222-4222-8222-222222222222"
    oid = "44444444-4444-4444-8444-444444444444"
    sp._PERSONALIZATION_CACHE.set(
        sp._cache_key(uid, oid),
        {"agent_name": "cached", "memory": "", "soul": ""},
    )
    monkeypatch.setattr(sp, "_valid_uuid", lambda _uid: True)
    monkeypatch.setattr(sp, "supabase_personalization_configured", lambda: True)
    monkeypatch.setattr(sp, "ensure_personal_org_sync", lambda _uid: oid)

    class FakeResp:
        def raise_for_status(self) -> None:
            return None

    class FakeClient:
        def post(self, *_args, **_kwargs):
            return FakeResp()

    monkeypatch.setattr(sp, "get_http_client", lambda: FakeClient())
    sp.upsert_personalization_sync(uid, "New", "mem", "soul", org_id=oid)
    assert sp._PERSONALIZATION_CACHE.get(sp._cache_key(uid, oid), ttl_seconds=300.0) is None
