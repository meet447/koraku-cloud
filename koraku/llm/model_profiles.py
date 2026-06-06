"""Load model metadata from ``models.json`` and derive per-model agent limits."""
from __future__ import annotations

import json
from contextvars import ContextVar, Token
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from koraku.core.config import settings

_MODELS_JSON = Path(__file__).resolve().parent / "models.json"
_FIREWORKS_PREFIX = "accounts/fireworks/models/"

_active_limits: ContextVar[ResolvedLimits | None] = ContextVar("koraku_model_limits", default=None)


@dataclass(frozen=True)
class ModelPricing:
    input_uncached_per_million: float | None = None
    input_cached_per_million: float | None = None
    output_per_million: float | None = None


@dataclass(frozen=True)
class ModelCapabilities:
    function_calling: bool = False
    vision: bool = False
    tunable: bool = False
    serverless: bool = False
    llm: bool = True

    def to_dict(self) -> dict[str, bool]:
        return {
            "function_calling": self.function_calling,
            "vision": self.vision,
            "tunable": self.tunable,
            "serverless": self.serverless,
            "llm": self.llm,
        }


@dataclass(frozen=True)
class ModelProfile:
    id: str
    name: str
    provider: str
    context_tokens: int
    max_output_tokens: int | None = None
    max_tool_result_chars: int | None = None
    context_max_messages: int | None = None
    context_summarize_after: int | None = None
    tool_bash_output_max_chars: int | None = None
    tool_web_fetch_max_chars: int | None = None
    pricing: ModelPricing | None = None
    capabilities: ModelCapabilities | None = None
    logo_url: str | None = None
    featured: bool = False
    ui_order: int = 999

    def to_ui_entry(self, *, limits: ResolvedLimits) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "id": self.id,
            "label": self.name,
            "context_tokens": self.context_tokens,
            "max_output_tokens": limits.max_output_tokens,
            "capabilities": (self.capabilities or ModelCapabilities()).to_dict(),
        }
        if self.logo_url:
            entry["logo_url"] = self.logo_url
        if self.pricing and (
            self.pricing.input_uncached_per_million is not None
            or self.pricing.output_per_million is not None
        ):
            entry["pricing"] = {
                k: v
                for k, v in {
                    "input_uncached_per_million": self.pricing.input_uncached_per_million,
                    "input_cached_per_million": self.pricing.input_cached_per_million,
                    "output_per_million": self.pricing.output_per_million,
                }.items()
                if v is not None
            }
        return entry


@dataclass(frozen=True)
class ResolvedLimits:
    model_id: str
    context_tokens: int
    max_output_tokens: int
    max_tool_result_chars: int
    context_max_messages: int
    context_summarize_after: int
    tool_bash_output_max_chars: int
    tool_web_fetch_max_chars: int


def _coerce_int(value: Any, fallback: int) -> int:
    try:
        parsed = int(value)
        return parsed if parsed > 0 else fallback
    except (TypeError, ValueError):
        return fallback


def _parse_capabilities(raw: dict[str, Any] | None) -> ModelCapabilities | None:
    if not raw:
        return None
    return ModelCapabilities(
        function_calling=bool(raw.get("function_calling")),
        vision=bool(raw.get("vision")),
        tunable=bool(raw.get("tunable")),
        serverless=bool(raw.get("serverless")),
        llm=bool(raw.get("llm", True)),
    )


def _parse_pricing(raw: dict[str, Any] | None) -> ModelPricing | None:
    if not raw:
        return None
    return ModelPricing(
        input_uncached_per_million=raw.get("input_uncached_per_million"),
        input_cached_per_million=raw.get("input_cached_per_million"),
        output_per_million=raw.get("output_per_million"),
    )


def _parse_profile(raw: dict[str, Any]) -> ModelProfile:
    return ModelProfile(
        id=str(raw["id"]),
        name=str(raw.get("name") or raw["id"]),
        provider=str(raw.get("provider") or "fireworks"),
        context_tokens=_coerce_int(raw.get("context_tokens"), settings.llm_context_tokens),
        max_output_tokens=raw.get("max_output_tokens"),
        max_tool_result_chars=raw.get("max_tool_result_chars"),
        context_max_messages=raw.get("context_max_messages"),
        context_summarize_after=raw.get("context_summarize_after"),
        tool_bash_output_max_chars=raw.get("tool_bash_output_max_chars"),
        tool_web_fetch_max_chars=raw.get("tool_web_fetch_max_chars"),
        pricing=_parse_pricing(raw.get("pricing")),
        capabilities=_parse_capabilities(raw.get("capabilities")),
        logo_url=raw.get("logo_url"),
        featured=bool(raw.get("featured")),
        ui_order=_coerce_int(raw.get("ui_order"), 999),
    )


@lru_cache(maxsize=1)
def _catalog() -> dict[str, Any]:
    with _MODELS_JSON.open(encoding="utf-8") as fh:
        return json.load(fh)


def reload_model_catalog() -> None:
    """Clear cached catalog (tests)."""
    _catalog.cache_clear()


@lru_cache(maxsize=1)
def _profiles_by_id() -> dict[str, ModelProfile]:
    data = _catalog()
    out: dict[str, ModelProfile] = {}
    for raw in data.get("models", []):
        profile = _parse_profile(raw)
        out[profile.id] = profile
    return out


def catalog_defaults() -> dict[str, int]:
    data = _catalog()
    raw = data.get("defaults") or {}
    return {
        "max_output_tokens": _coerce_int(raw.get("max_output_tokens"), settings.max_tokens),
        "max_tool_result_chars": _coerce_int(
            raw.get("max_tool_result_chars"), settings.max_tool_result_chars
        ),
        "context_max_messages": _coerce_int(
            raw.get("context_max_messages"), settings.context_max_messages
        ),
        "context_summarize_after": _coerce_int(
            raw.get("context_summarize_after"), settings.context_summarize_after
        ),
        "tool_bash_output_max_chars": _coerce_int(
            raw.get("tool_bash_output_max_chars"), settings.tool_bash_output_max_chars
        ),
        "tool_web_fetch_max_chars": _coerce_int(
            raw.get("tool_web_fetch_max_chars"), settings.tool_web_fetch_max_chars
        ),
    }


def get_model_profile(model_id: str | None) -> ModelProfile | None:
    mid = (model_id or "").strip()
    if not mid:
        return None
    return _profiles_by_id().get(mid)


def list_fireworks_featured() -> list[ModelProfile]:
    featured = [p for p in _profiles_by_id().values() if p.provider == "fireworks" and p.featured]
    return sorted(featured, key=lambda p: (p.ui_order, p.name.lower()))


def fireworks_model_ids() -> frozenset[str]:
    return frozenset(
        p.id for p in _profiles_by_id().values() if p.provider == "fireworks"
    )


def is_known_fireworks_model(model_id: str | None) -> bool:
    mid = (model_id or "").strip()
    if not mid:
        return False
    if mid in fireworks_model_ids():
        return True
    return mid.startswith(_FIREWORKS_PREFIX)


def _derive_from_context(context_tokens: int, defaults: dict[str, int]) -> dict[str, int]:
    ctx = max(1, context_tokens)
    return {
        "max_output_tokens": min(defaults["max_output_tokens"], max(4096, ctx // 2)),
        "max_tool_result_chars": min(defaults["max_tool_result_chars"], max(8000, int(ctx * 0.49))),
        "context_max_messages": max(28, min(80, ctx // 4500)),
        "context_summarize_after": max(14, min(40, ctx // 9000)),
        "tool_bash_output_max_chars": min(
            defaults["tool_bash_output_max_chars"],
            max(4000, ctx // 8),
        ),
        "tool_web_fetch_max_chars": min(
            defaults["tool_web_fetch_max_chars"],
            max(8000, ctx // 8),
        ),
    }


@lru_cache(maxsize=1)
def _sdk_field_defaults() -> dict[str, int]:
    from koraku.core.sdk_settings import SdkSettings

    out: dict[str, int] = {}
    for name in (
        "max_tokens",
        "max_tool_result_chars",
        "context_max_messages",
        "context_summarize_after",
        "tool_bash_output_max_chars",
        "tool_web_fetch_max_chars",
        "llm_context_tokens",
    ):
        field = SdkSettings.model_fields[name]
        out[name] = _coerce_int(field.default, 0)
    return out


def _settings_env_override(settings_attr: str) -> bool:
    defaults = _sdk_field_defaults()
    return int(getattr(settings, settings_attr)) != defaults[settings_attr]


def resolve_limits(model_id: str | None, provider_id: str | None = None) -> ResolvedLimits:
    """Resolve agent limits for a model; explicit env overrides win over catalog."""
    defaults = catalog_defaults()
    profile = get_model_profile(model_id)
    if profile:
        context_tokens = profile.context_tokens
    else:
        context_tokens = int(settings.llm_context_tokens)

    derived = _derive_from_context(context_tokens, defaults)

    field_map = {
        "max_output_tokens": ("max_output_tokens", "max_tokens"),
        "max_tool_result_chars": ("max_tool_result_chars", "max_tool_result_chars"),
        "context_max_messages": ("context_max_messages", "context_max_messages"),
        "context_summarize_after": ("context_summarize_after", "context_summarize_after"),
        "tool_bash_output_max_chars": ("tool_bash_output_max_chars", "tool_bash_output_max_chars"),
        "tool_web_fetch_max_chars": ("tool_web_fetch_max_chars", "tool_web_fetch_max_chars"),
    }

    resolved_values: dict[str, int] = {}
    for key, (profile_field, settings_attr) in field_map.items():
        if _settings_env_override(settings_attr):
            resolved_values[key] = int(getattr(settings, settings_attr))
            continue
        if profile is not None:
            profile_val = getattr(profile, profile_field, None)
            if profile_val is not None:
                resolved_values[key] = int(profile_val)
                continue
        resolved_values[key] = int(derived.get(key, defaults.get(key, getattr(settings, settings_attr))))

    mid = (model_id or "").strip() or (profile.id if profile else settings.fireworks_model)
    return ResolvedLimits(
        model_id=mid,
        context_tokens=context_tokens,
        max_output_tokens=resolved_values["max_output_tokens"],
        max_tool_result_chars=resolved_values["max_tool_result_chars"],
        context_max_messages=resolved_values["context_max_messages"],
        context_summarize_after=resolved_values["context_summarize_after"],
        tool_bash_output_max_chars=resolved_values["tool_bash_output_max_chars"],
        tool_web_fetch_max_chars=resolved_values["tool_web_fetch_max_chars"],
    )


def configure_context_manager(cm: Any, model_id: str, provider_id: str | None = None) -> ResolvedLimits:
    """Apply resolved limits to an existing :class:`~koraku.agent.context_manager.ContextManager`."""
    limits = resolve_limits(model_id, provider_id)
    cm.max_messages = limits.context_max_messages
    cm.summarize_after = limits.context_summarize_after
    cm.max_tool_result_chars = limits.max_tool_result_chars
    return limits


def set_active_limits(limits: ResolvedLimits | None) -> Token[ResolvedLimits | None]:
    return _active_limits.set(limits)


def reset_active_limits(token: Token[ResolvedLimits | None]) -> None:
    _active_limits.reset(token)


def get_active_limits() -> ResolvedLimits | None:
    return _active_limits.get()


def active_tool_bash_output_max_chars() -> int:
    lim = get_active_limits()
    if lim is not None:
        return lim.tool_bash_output_max_chars
    return int(settings.tool_bash_output_max_chars)


def active_tool_web_fetch_max_chars() -> int:
    lim = get_active_limits()
    if lim is not None:
        return lim.tool_web_fetch_max_chars
    return int(settings.tool_web_fetch_max_chars)


__all__ = [
    "ModelCapabilities",
    "ModelPricing",
    "ModelProfile",
    "ResolvedLimits",
    "active_tool_bash_output_max_chars",
    "active_tool_web_fetch_max_chars",
    "catalog_defaults",
    "configure_context_manager",
    "fireworks_model_ids",
    "get_active_limits",
    "get_model_profile",
    "is_known_fireworks_model",
    "list_fireworks_featured",
    "reload_model_catalog",
    "reset_active_limits",
    "resolve_limits",
    "set_active_limits",
]
