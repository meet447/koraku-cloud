"""Tests for curated Composio integration catalog."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from koraku.integrations import composio
from koraku.integrations.composio_curated_toolkits import CURATED_TOOLKITS


def test_list_curated_toolkits_static_returns_all_manifest_entries() -> None:
    items = composio.list_curated_toolkits_static()
    assert len(items) == len(CURATED_TOOLKITS)
    assert items[0]["slug"] == "GMAIL"
    assert items[0]["category"] == "collab"
    assert items[0]["icon_slug"] == "gmail"


def test_list_curated_toolkits_static_filters_by_query() -> None:
    items = composio.list_curated_toolkits_static(query="github")
    assert len(items) == 1
    assert items[0]["slug"] == "GITHUB"


def test_list_curated_toolkits_resolves_only_supported_slugs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(composio, "is_configured", lambda: True)

    class FakeToolkits:
        def get(self, slug: str):
            if slug == "GMAIL":
                return SimpleNamespace(
                    name="Gmail",
                    meta=SimpleNamespace(description="Email from Composio"),
                )
            raise RuntimeError("not found")

    class FakeClient:
        toolkits = FakeToolkits()

    monkeypatch.setattr(composio, "_client", lambda: FakeClient())
    composio._curated_toolkits_cache = None

    items = composio.list_curated_toolkits()
    assert len(items) == 1
    assert items[0]["slug"] == "GMAIL"
    assert items[0]["name"] == "Gmail"
    assert "Composio" in items[0]["description"]

    filtered = composio.list_curated_toolkits(query="slack")
    assert filtered == []
