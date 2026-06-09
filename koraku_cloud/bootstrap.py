"""Load SDK + Cloud settings when the product server starts."""
from __future__ import annotations

from koraku.core.config import bind_cloud_settings, configure_sdk
from koraku.core.product_hooks import ProductHooks, register_product_hooks
from koraku.core.sdk_settings import SdkSettings
from koraku_cloud.cloud_settings import CloudSettings
from koraku_cloud import product_hooks as cloud_product_hooks


def bootstrap_cloud() -> tuple[SdkSettings, CloudSettings]:
    """Bind agent (SDK) and product (Cloud) config from the repo ``.env``."""
    sdk = SdkSettings()
    cloud = CloudSettings()
    configure_sdk(sdk)
    bind_cloud_settings(cloud)
    register_product_hooks(
        ProductHooks(
            hydrate_session_for_turn=cloud_product_hooks.hydrate_session_for_turn,
            fetch_account_personalization=cloud_product_hooks.fetch_account_personalization,
            after_turn_memory_ingest=cloud_product_hooks.after_turn_memory_ingest,
            resolve_tenant_org=cloud_product_hooks.resolve_tenant_org,
            health_detail_extras=cloud_product_hooks.health_detail_extras,
            extra_agent_tools=cloud_product_hooks.extra_agent_tools,
            configure_automation_scheduler=cloud_product_hooks.configure_automation_scheduler,
            start_automation_scheduler=cloud_product_hooks.start_automation_scheduler,
            shutdown_automation_scheduler=cloud_product_hooks.shutdown_automation_scheduler,
        )
    )
    return sdk, cloud
