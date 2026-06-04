"""Test defaults: SDK settings only unless a test binds Cloud."""
from __future__ import annotations

import pytest

from koraku.core.config import configure_sdk, reset_cloud_binding, reset_settings_caches
from koraku.sdk import KorakuConfig


@pytest.fixture(autouse=True)
def _sdk_settings_for_tests() -> None:
    reset_cloud_binding()
    configure_sdk(KorakuConfig().to_sdk_settings())
    reset_settings_caches()
    yield
    reset_cloud_binding()
    configure_sdk(KorakuConfig().to_sdk_settings())
    reset_settings_caches()
