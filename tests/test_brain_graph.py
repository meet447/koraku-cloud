"""Brain memory graph payload builders."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from koraku.core.config import Settings, configure
from koraku.integrations import brain_graph as bg


@pytest.fixture(autouse=True)
def _settings():
    configure(Settings(supermemory_api_key="test-key"))
    yield
    configure(Settings())


def test_synthetic_from_explicit_memory() -> None:
    docs = bg._profile_fallback_documents(
        profile=None,
        space_tag="koraku-u1",
        explicit_memory="- Prefers dark mode\n- Uses vim",
        explicit_soul="Warm and direct",
    )
    assert len(docs) == 2
    assert docs[0]["title"] == "Explicit preferences"
    assert any("dark mode" in m["memory"] for d in docs for m in d["memories"])


def test_fetch_brain_graph_uses_documents(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_docs = [
        {
            "id": "doc-1",
            "title": "Chat turn",
            "documentType": "text",
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-01T00:00:00Z",
            "memories": [{"id": "m1", "memory": "User likes TypeScript", "createdAt": "2026-01-01T00:00:00Z", "updatedAt": "2026-01-01T00:00:00Z"}],
        }
    ]

    def _fake_fetch(tag: str, *, page: int, limit: int):
        return fake_docs, {"currentPage": 1, "limit": limit, "totalItems": 1, "totalPages": 1}

    monkeypatch.setattr(bg, "_fetch_supermemory_documents", _fake_fetch)
    out = bg.fetch_brain_graph_sync("user-1", org_id="org-1")
    assert out["source"] == "supermemory"
    assert len(out["documents"]) == 1
    assert out["documents"][0]["memories"][0]["memory"] == "User likes TypeScript"


def test_fetch_brain_graph_profile_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bg, "_fetch_supermemory_documents", lambda *a, **k: ([], {"currentPage": 1, "limit": 100, "totalItems": 0, "totalPages": 0}))
    profile = SimpleNamespace(
        profile=SimpleNamespace(static=["Senior engineer"], dynamic=["Building Koraku"]),
    )
    with patch.object(bg, "_client") as mock_client:
        mock_client.return_value.profile.return_value = profile
        out = bg.fetch_brain_graph_sync("user-1")
    assert out["source"] == "profile_fallback"
    assert len(out["documents"]) >= 1
