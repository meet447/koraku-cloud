"""Named OpenAI-compatible LLM providers from environment variables."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from koraku.core.config import settings

_PROVIDER_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")

# Provider id -> env var prefix (default: id uppercased with - -> _)
_ENV_PREFIX_ALIASES: dict[str, str] = {"custom": "CUSTOM"}


@dataclass(frozen=True)
class OpenAICompatProvider:
    id: str
    label: str
    base_url: str
    api_key: str
    default_model: str
    models: tuple[str, ...]


def _normalize_id(raw: str) -> str:
    pid = (raw or "").strip().lower()
    if pid == "custom_openai":
        return "custom"
    return pid


def _valid_id(provider_id: str) -> bool:
    return bool(_PROVIDER_ID_RE.match(provider_id))


def _env_prefix(provider_id: str) -> str:
    return _ENV_PREFIX_ALIASES.get(provider_id, provider_id.upper().replace("-", "_"))


def _read_env(name: str) -> str:
    return (os.environ.get(name, "") or "").strip()


def _split_models(raw: str) -> list[str]:
    return [m.strip() for m in raw.split(",") if m.strip()]


def _provider_from_env(provider_id: str) -> OpenAICompatProvider | None:
    pid = _normalize_id(provider_id)
    if not _valid_id(pid):
        return None
    prefix = _env_prefix(pid)
    base_url = _read_env(f"{prefix}_BASE_URL")
    if not base_url:
        return None
    api_key = _read_env(f"{prefix}_API_KEY")
    default_model = _read_env(f"{prefix}_MODEL") or "gpt-4o-mini"
    models_raw = _read_env(f"{prefix}_MODELS")
    models = _split_models(models_raw) if models_raw else [default_model]
    if default_model not in models:
        models = [default_model, *models]
    label = _read_env(f"{prefix}_LABEL") or pid.replace("_", " ").title()
    return OpenAICompatProvider(
        id=pid,
        label=label,
        base_url=base_url.rstrip("/"),
        api_key=api_key,
        default_model=default_model,
        models=tuple(models),
    )


def _providers_from_json(raw: str) -> dict[str, OpenAICompatProvider]:
    if not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, list):
        return {}
    out: dict[str, OpenAICompatProvider] = {}
    for item in payload:
        if not isinstance(item, dict):
            continue
        pid = _normalize_id(str(item.get("id", "")))
        base_url = str(item.get("base_url", "")).strip().rstrip("/")
        if not _valid_id(pid) or not base_url:
            continue
        default_model = str(item.get("default_model") or item.get("model") or "gpt-4o-mini").strip()
        models_raw = item.get("models")
        if isinstance(models_raw, list):
            models = [str(m).strip() for m in models_raw if str(m).strip()]
        elif isinstance(models_raw, str):
            models = _split_models(models_raw)
        else:
            models = [default_model]
        if default_model not in models:
            models = [default_model, *models]
        label = str(item.get("label") or pid.replace("_", " ").title()).strip()
        out[pid] = OpenAICompatProvider(
            id=pid,
            label=label,
            base_url=base_url,
            api_key=str(item.get("api_key", "")).strip(),
            default_model=default_model,
            models=tuple(models),
        )
    return out


def _configured_ids_from_env() -> list[str]:
    raw = _read_env("LLM_OPENAI_COMPAT_IDS") or (settings.llm_openai_compat_ids or "").strip()
    ids = [_normalize_id(x) for x in raw.split(",") if _normalize_id(x)] if raw else []
    if _read_env("CUSTOM_BASE_URL") and "custom" not in ids:
        ids.append("custom")
    return ids


@lru_cache(maxsize=1)
def load_openai_compat_providers() -> dict[str, OpenAICompatProvider]:
    providers: dict[str, OpenAICompatProvider] = {}
    for pid in _configured_ids_from_env():
        prov = _provider_from_env(pid)
        if prov:
            providers[pid] = prov
    json_raw = _read_env("LLM_OPENAI_COMPAT_JSON") or (settings.llm_openai_compat_json or "").strip()
    for pid, prov in _providers_from_json(json_raw).items():
        providers[pid] = prov
    return providers


def reload_openai_compat_providers() -> None:
    load_openai_compat_providers.cache_clear()


def get_openai_compat_provider(provider_id: str) -> OpenAICompatProvider | None:
    pid = _normalize_id(provider_id)
    return load_openai_compat_providers().get(pid)


def is_openai_compat_provider(provider_id: str) -> bool:
    return get_openai_compat_provider(provider_id) is not None


def openai_compat_provider_ids() -> list[str]:
    return list(load_openai_compat_providers().keys())


def ui_block_for_openai_compat(provider: OpenAICompatProvider) -> dict[str, Any]:
    entries = [{"id": m, "label": m} for m in provider.models]
    return {
        "id": provider.id,
        "label": provider.label,
        "configured": True,
        "default_model": provider.default_model,
        "models": list(provider.models),
        "entries": entries,
    }
