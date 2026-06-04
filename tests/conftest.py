"""Test defaults: SDK settings only unless a test binds Cloud."""
from __future__ import annotations

import pytest

from koraku.core.auth import reset_auth_verifier
from koraku.core.config import configure_sdk, reset_cloud_binding
from koraku.plugins.memory import reset_memory_backend_cache
from koraku.sdk import KorakuConfig


@pytest.fixture(autouse=True)
def _sdk_settings_for_tests() -> None:
    reset_cloud_binding()
    configure_sdk(KorakuConfig().to_sdk_settings())
    reset_memory_backend_cache()
    reset_auth_verifier()
    yield
    reset_cloud_binding()
    configure_sdk(KorakuConfig().to_sdk_settings())
    reset_memory_backend_cache()
    reset_auth_verifier()
