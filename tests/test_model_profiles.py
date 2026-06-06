"""Tests for koraku/llm/models.json catalog and limit resolution."""

from __future__ import annotations

import pytest

from koraku.core.config import Settings, use_settings
from koraku.core.sdk_settings import SdkSettings
from koraku.llm.canonical import CanonicalChatRequest
from koraku.llm.catalog import ui_chat_models
from koraku.llm.model_profiles import (
    get_model_profile,
    list_fireworks_featured,
    reload_model_catalog,
    resolve_limits,
)


@pytest.fixture(autouse=True)
def _fresh_catalog() -> None:
    reload_model_catalog()


def test_kimi_profile_has_262k_context() -> None:
    profile = get_model_profile("accounts/fireworks/models/kimi-k2p6")
    assert profile is not None
    assert profile.name == "Kimi K2.6"
    assert profile.context_tokens == 262_000
    assert profile.max_output_tokens == 128_000
    assert profile.capabilities is not None
    assert profile.capabilities.vision is True


def test_resolve_limits_uses_model_profile() -> None:
    limits = resolve_limits("accounts/fireworks/models/minimax-m2p7")
    assert limits.context_tokens == 196_000
    assert limits.max_output_tokens == 98_000
    assert limits.context_max_messages >= 28


def test_canonical_for_turn_uses_model_max_output() -> None:
    req = CanonicalChatRequest.for_turn(
        model_id="accounts/fireworks/models/minimax-m2p7",
        messages=[],
        tool_schemas=[],
        system_prompt=None,
    )
    assert req.max_tokens == 98_000


def test_featured_fireworks_models_for_ui() -> None:
    featured = list_fireworks_featured()
    assert len(featured) == 4
    assert featured[0].id == "accounts/fireworks/models/kimi-k2p6"


def test_ui_chat_models_includes_profile_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIREWORKS_API_KEY", "fw-key")
    with use_settings(Settings(fireworks_api_key="fw-key", llm_provider="fireworks")):
        data = ui_chat_models()
    fw = next(p for p in data["providers"] if p["id"] == "fireworks")
    kimi = next(e for e in fw["entries"] if e["id"] == "accounts/fireworks/models/kimi-k2p6")
    assert kimi["label"] == "Kimi K2.6"
    assert kimi["context_tokens"] == 262_000
    assert kimi["max_output_tokens"] == 128_000
    assert kimi["capabilities"]["function_calling"] is True


def test_settings_override_wins_over_profile() -> None:
    packaged = SdkSettings()
    with use_settings(Settings(max_tokens=packaged.max_tokens + 1)):
        limits = resolve_limits("accounts/fireworks/models/kimi-k2p6")
    assert limits.max_output_tokens == packaged.max_tokens + 1
