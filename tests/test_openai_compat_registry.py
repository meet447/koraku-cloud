"""Tests for named OpenAI-compatible provider registry."""
from __future__ import annotations

import json

import pytest

from koraku.core.config import Settings, configure, use_settings
from koraku.llm.catalog import configured_provider_ids, is_provider_configured, ui_chat_models
from koraku.llm.client import UnifiedLLMClient
from koraku.llm.openai_compat_registry import (
    get_openai_compat_provider,
    load_openai_compat_providers,
    reload_openai_compat_providers,
)


@pytest.fixture(autouse=True)
def _reset_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "LLM_OPENAI_COMPAT_IDS",
        "LLM_OPENAI_COMPAT_JSON",
        "OPENAI_BASE_URL",
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "CUSTOM_BASE_URL",
        "CUSTOM_MODEL",
        "CUSTOM_API_KEY",
        "FIREWORKS_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    reload_openai_compat_providers()
    yield
    reload_openai_compat_providers()


def test_registry_from_prefixed_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_OPENAI_COMPAT_IDS", "openai,groq")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_MODELS", "gpt-4o-mini,gpt-4o")
    monkeypatch.setenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    reload_openai_compat_providers()

    providers = load_openai_compat_providers()
    assert set(providers) == {"openai", "groq"}
    assert providers["openai"].default_model == "gpt-4o-mini"
    assert providers["openai"].models == ("gpt-4o-mini", "gpt-4o")
    assert providers["groq"].base_url == "https://api.groq.com/openai/v1"


def test_custom_env_auto_registers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CUSTOM_BASE_URL", "http://127.0.0.1:1234/v1")
    monkeypatch.setenv("CUSTOM_MODEL", "llama-3.3-70b")
    reload_openai_compat_providers()

    prov = get_openai_compat_provider("custom")
    assert prov is not None
    assert prov.base_url == "http://127.0.0.1:1234/v1"
    assert prov.default_model == "llama-3.3-70b"


def test_custom_openai_id_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_OPENAI_COMPAT_IDS", "custom_openai")
    monkeypatch.setenv("CUSTOM_BASE_URL", "http://127.0.0.1:1234/v1")
    monkeypatch.setenv("CUSTOM_MODEL", "llama-3.3-70b")
    reload_openai_compat_providers()

    assert get_openai_compat_provider("custom") is not None


def test_registry_from_json(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = [
        {
            "id": "together",
            "label": "Together AI",
            "base_url": "https://api.together.xyz/v1",
            "api_key": "together-key",
            "default_model": "meta-llama/Llama-3-70b-chat-hf",
            "models": ["meta-llama/Llama-3-70b-chat-hf"],
        }
    ]
    monkeypatch.setenv("LLM_OPENAI_COMPAT_JSON", json.dumps(payload))
    reload_openai_compat_providers()

    prov = get_openai_compat_provider("together")
    assert prov is not None
    assert prov.label == "Together AI"


def test_ui_lists_openai_compat_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_OPENAI_COMPAT_IDS", "openai")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("FIREWORKS_API_KEY", "fw-key")
    reload_openai_compat_providers()

    with use_settings(Settings(fireworks_api_key="fw-key", llm_provider="fireworks")):
        data = ui_chat_models()
        ids = [p["id"] for p in data["providers"]]
        assert "fireworks" in ids
        assert "openai" in ids


def test_unified_client_resolves_named_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_OPENAI_COMPAT_IDS", "openai")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    reload_openai_compat_providers()

    client = UnifiedLLMClient(provider_override="openai")
    assert client.provider == "openai"
    assert client.model == "gpt-4o-mini"


def test_configured_providers_include_fireworks_and_compat(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIREWORKS_API_KEY", "fw-key")
    monkeypatch.setenv("LLM_OPENAI_COMPAT_IDS", "openai")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    reload_openai_compat_providers()

    with use_settings(Settings(fireworks_api_key="fw-key")):
        ids = configured_provider_ids()
        assert "fireworks" in ids
        assert "openai" in ids
        assert is_provider_configured("openai")
