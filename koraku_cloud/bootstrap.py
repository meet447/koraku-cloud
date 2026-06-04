"""Load SDK + Cloud settings when the product server starts."""
from __future__ import annotations

from koraku.core.config import bind_cloud_settings, configure_sdk
from koraku.core.sdk_settings import SdkSettings
from koraku_cloud.cloud_settings import CloudSettings


def bootstrap_cloud() -> tuple[SdkSettings, CloudSettings]:
    """Bind agent (SDK) and product (Cloud) config from the repo ``.env``."""
    sdk = SdkSettings()
    cloud = CloudSettings()
    configure_sdk(sdk)
    bind_cloud_settings(cloud)
    return sdk, cloud
