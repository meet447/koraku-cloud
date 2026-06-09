"""Optional product-layer hooks (Cloud SaaS). Unset hooks → SDK behavior."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

HydrateSessionFn = Callable[..., Awaitable[Any]]
FetchPersonalizationFn = Callable[..., Awaitable[dict[str, str] | None]]
FetchOrgSkillsFn = Callable[..., Awaitable[list[dict[str, str]] | None]]
AfterTurnMemoryFn = Callable[..., Awaitable[None]]
ResolveTenantOrgFn = Callable[[Any, str], tuple[str | None, str | None]]
HealthDetailExtrasFn = Callable[[], dict[str, object]]
ExtraAgentToolsFn = Callable[[], list[Any]]
ConfigureAutomationSchedulerFn = Callable[[Any | None], None]
StartAutomationSchedulerFn = Callable[[], None]
ShutdownAutomationSchedulerFn = Callable[[], None]

_registered: ProductHooks | None = None


@dataclass(frozen=True)
class ProductHooks:
    hydrate_session_for_turn: HydrateSessionFn | None = None
    fetch_account_personalization: FetchPersonalizationFn | None = None
    fetch_org_skills: FetchOrgSkillsFn | None = None
    after_turn_memory_ingest: AfterTurnMemoryFn | None = None
    resolve_tenant_org: ResolveTenantOrgFn | None = None
    health_detail_extras: HealthDetailExtrasFn | None = None
    extra_agent_tools: ExtraAgentToolsFn | None = None
    configure_automation_scheduler: ConfigureAutomationSchedulerFn | None = None
    start_automation_scheduler: StartAutomationSchedulerFn | None = None
    shutdown_automation_scheduler: ShutdownAutomationSchedulerFn | None = None


def register_product_hooks(hooks: ProductHooks) -> None:
    global _registered
    _registered = hooks


def clear_product_hooks() -> None:
    global _registered
    _registered = None


def product_hooks_active() -> bool:
    return _registered is not None


def runtime_mode_label() -> str:
    """``cloud`` when the product layer registered hooks; else ``sdk``."""
    return "cloud" if product_hooks_active() else "sdk"


def resolve_tenant_org(request: Any, sub: str) -> tuple[str | None, str | None]:
    if _registered is not None and _registered.resolve_tenant_org is not None:
        return _registered.resolve_tenant_org(request, sub)
    return None, None


def health_detail_extras() -> dict[str, object]:
    if _registered is not None and _registered.health_detail_extras is not None:
        return _registered.health_detail_extras()
    return {}


def extra_agent_tools() -> list[Any]:
    if _registered is not None and _registered.extra_agent_tools is not None:
        return list(_registered.extra_agent_tools())
    return []


async def hydrate_session_for_turn(*args: Any, **kwargs: Any) -> Any:
    if _registered is not None and _registered.hydrate_session_for_turn is not None:
        return await _registered.hydrate_session_for_turn(*args, **kwargs)
    from koraku.api.sdk_session_hydration import hydrate_sdk_session_for_turn

    return await hydrate_sdk_session_for_turn(*args, **kwargs)


async def fetch_account_personalization(*args: Any, **kwargs: Any) -> dict[str, str] | None:
    if _registered is not None and _registered.fetch_account_personalization is not None:
        return await _registered.fetch_account_personalization(*args, **kwargs)
    return None


async def fetch_org_skills(*args: Any, **kwargs: Any) -> list[dict[str, str]] | None:
    if _registered is not None and _registered.fetch_org_skills is not None:
        return await _registered.fetch_org_skills(*args, **kwargs)
    return None


async def after_turn_memory_ingest(*args: Any, **kwargs: Any) -> None:
    if _registered is not None and _registered.after_turn_memory_ingest is not None:
        await _registered.after_turn_memory_ingest(*args, **kwargs)
