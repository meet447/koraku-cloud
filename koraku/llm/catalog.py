"""Chat model catalog for the web UI and provider resolution."""
from typing import Any

from koraku.core.config import settings
from koraku.llm.openai_compat_registry import (
    get_openai_compat_provider,
    is_openai_compat_provider,
    load_openai_compat_providers,
    openai_compat_provider_ids,
    ui_block_for_openai_compat,
)

_BUILTIN_PROVIDER_IDS = frozenset({"anthropic", "fireworks"})

# Only models exposed in the Fireworks composer picker (order = UI order).
_FIREWORKS_CURATED: list[dict[str, str]] = [
    {
        "id": "accounts/fireworks/models/kimi-k2p6",
        "logo_url": "https://app.fireworks.ai/images/logos/moonshot-icon.svg",
        "label": "Kimi K2",
    },
    {
        "id": "accounts/fireworks/models/qwen3p6-plus",
        "logo_url": "https://app.fireworks.ai/images/logos/qwen-icon.svg",
        "label": "Qwen3 6 Plus",
    },
    {
        "id": "accounts/fireworks/models/minimax-m2p7",
        "logo_url": "https://app.fireworks.ai/images/logos/minimax-icon.svg",
        "label": "MiniMax M2",
    },
    {
        "id": "accounts/fireworks/models/glm-5p1",
        "logo_url": "https://app.fireworks.ai/images/logos/z-ai.svg",
        "label": "GLM 5.1",
    },
]

_FIREWORKS_CURATED_BY_ID: dict[str, dict[str, str]] = {e["id"]: e for e in _FIREWORKS_CURATED}


def known_provider_ids() -> frozenset[str]:
    return _BUILTIN_PROVIDER_IDS | frozenset(load_openai_compat_providers().keys())


def _fireworks_curated_ids() -> list[str]:
    return [e["id"] for e in _FIREWORKS_CURATED]


def _normalize_fireworks_model_id(model_id: str | None) -> str:
    m = (model_id or "").strip()
    if m in _FIREWORKS_CURATED_BY_ID:
        return m
    return _fireworks_curated_ids()[0]


def _fireworks_ui_block() -> dict[str, Any]:
    pid = "fireworks"
    configured = is_provider_configured(pid)
    default_model = _normalize_fireworks_model_id(settings.fireworks_model)
    models = _fireworks_curated_ids()
    entries = [dict(e) for e in _FIREWORKS_CURATED]
    return {
        "id": pid,
        "label": "Fireworks",
        "configured": configured,
        "default_model": default_model,
        "models": models,
        "entries": entries,
    }


def _anthropic_ui_block() -> dict[str, Any]:
    pid = "anthropic"
    model = settings.anthropic_model
    return {
        "id": pid,
        "label": "Anthropic",
        "configured": is_provider_configured(pid),
        "default_model": model,
        "models": [model],
        "entries": [{"id": model, "label": model}],
    }


def is_provider_configured(provider_id: str) -> bool:
    p = (provider_id or "").strip().lower()
    if p == "anthropic":
        return bool((settings.anthropic_api_key or "").strip())
    if p == "fireworks":
        return bool((settings.fireworks_api_key or "").strip() and (settings.fireworks_base_url or "").strip())
    if is_openai_compat_provider(p):
        return True
    return False


def default_model_for_provider(provider_id: str | None) -> str:
    p = (provider_id or settings.llm_provider or "fireworks").strip().lower()
    if p == "anthropic":
        return settings.anthropic_model
    if p == "fireworks":
        return _normalize_fireworks_model_id(settings.fireworks_model)
    compat = get_openai_compat_provider(p)
    if compat:
        return compat.default_model
    return "gpt-4o-mini"


def default_chat_model() -> str:
    active = (settings.llm_provider or "fireworks").strip().lower()
    if is_provider_configured(active):
        return default_model_for_provider(active)
    ids = configured_provider_ids()
    if ids:
        return default_model_for_provider(ids[0])
    return default_model_for_provider("fireworks")


def resolve_effective_model(override: str | None, provider_id: str | None = None) -> str:
    o = (override or "").strip()
    pid = (provider_id or settings.llm_provider or "fireworks").strip().lower()
    if o:
        if pid == "fireworks" and o not in _FIREWORKS_CURATED_BY_ID:
            return _normalize_fireworks_model_id(settings.fireworks_model)
        return o
    return default_model_for_provider(provider_id)


def resolve_provider_id(provider: str | None) -> str:
    """Pick a configured provider id, falling back to defaults when needed."""
    active = (settings.llm_provider or "fireworks").strip().lower()
    eff_provider = (provider or "").strip().lower() or active
    if eff_provider not in known_provider_ids():
        eff_provider = active
    if not is_provider_configured(eff_provider):
        ids = configured_provider_ids()
        eff_provider = ids[0] if ids else active
    if eff_provider not in known_provider_ids():
        eff_provider = active
    return eff_provider


def resolve_provider_and_model(provider: str | None, model: str | None) -> tuple[str, str]:
    eff_provider = resolve_provider_id(provider)
    resolved_model = resolve_effective_model(model, provider_id=eff_provider)
    return eff_provider, resolved_model


def ui_chat_models() -> dict[str, Any]:
    active = (settings.llm_provider or "fireworks").strip().lower()
    providers: list[dict[str, Any]] = []

    fw = _fireworks_ui_block()
    providers.append(fw)

    anthropic = _anthropic_ui_block()
    if anthropic["configured"] or anthropic["id"] == active:
        providers.append(anthropic)

    for compat in load_openai_compat_providers().values():
        if compat.id == "custom" and fw["configured"]:
            continue
        providers.append(ui_block_for_openai_compat(compat))

    default_provider = active if is_provider_configured(active) else (
        configured_provider_ids()[0] if configured_provider_ids() else "fireworks"
    )
    default_model = default_model_for_provider(default_provider)
    flat_models = [m for block in providers for m in block.get("models", [])]

    return {
        "active_provider": default_provider,
        "default_model": default_model,
        "models": flat_models,
        "providers": providers,
    }


def configured_provider_ids() -> list[str]:
    out: list[str] = []
    for pid in ("fireworks", "anthropic"):
        if is_provider_configured(pid):
            out.append(pid)
    for pid in openai_compat_provider_ids():
        if pid not in out:
            out.append(pid)
    return out


def any_llm_configured() -> bool:
    return len(configured_provider_ids()) > 0
