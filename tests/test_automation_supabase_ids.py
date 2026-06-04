"""PostgREST filters must reject malformed automation/run UUIDs."""
from __future__ import annotations

from koraku_cloud.automations import supabase_store as store


def test_get_automation_for_event_rejects_invalid_id() -> None:
    assert store.get_automation_for_event("not-a-uuid") is None
    assert store.get_automation_for_event("id=eq.other") is None


def test_get_event_webhook_hash_rejects_invalid_id() -> None:
    assert store.get_event_webhook_hash("';drop--") is None


def test_get_automation_accepts_valid_uuid(monkeypatch) -> None:
    called: list[str] = []

    class _Resp:
        status_code = 200

        def json(self):
            return []

        def raise_for_status(self):
            return None

    class _Client:
        def get(self, url, headers=None):
            called.append(url)
            return _Resp()

    monkeypatch.setattr(store, "_client", lambda: _Client())
    monkeypatch.setattr(store, "_rest_url", lambda q: q)
    monkeypatch.setattr(store, "_headers", lambda: {})
    uid = "9c77f10c-fc6a-402f-8749-e3e65779b688"
    aid = "21ccb3a7-6567-49ea-9885-094673275af2"
    store.get_automation(uid, aid, org_id="00000000-0000-0000-0000-000000000001")
    assert called
    assert "id=eq.21ccb3a7-6567-49ea-9885-094673275af2" in called[0]
