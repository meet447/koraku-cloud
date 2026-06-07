import pytest
import sys
import logging
from koraku.server_core import warn_startup_profile
from koraku.core.config import configure, get_settings

@pytest.fixture(autouse=True)
def reset_config():
    configure()

def test_warn_startup_profile_no_product_hooks(mocker, caplog):
    caplog.set_level(logging.INFO)
    mocker.patch("koraku.server_core.product_hooks_active", return_value=False)
    warn_startup_profile()
    assert "Koraku SDK HTTP server (no Supabase product routes)" in caplog.text

def test_warn_startup_profile_missing_koraku_cloud(mocker, caplog):
    caplog.set_level(logging.WARNING)
    mocker.patch("koraku.server_core.product_hooks_active", return_value=True)
    mocker.patch.dict("sys.modules", {"koraku_cloud.integrations.supabase_tenant": None})
    warn_startup_profile()
    assert "koraku_cloud is not installed — Cloud product routes require the monorepo or koraku-cloud package" in caplog.text

def test_warn_startup_profile_tenant_not_configured(mocker, caplog):
    caplog.set_level(logging.WARNING)
    mocker.patch("koraku.server_core.product_hooks_active", return_value=True)
    mock_supabase_tenant_configured = mocker.MagicMock(return_value=False)
    mocker.patch.dict("sys.modules", {
        "koraku_cloud.integrations.supabase_tenant": mocker.MagicMock(
            supabase_tenant_configured=mock_supabase_tenant_configured
        )
    })

    warn_startup_profile()
    assert "Supabase tenant storage is not configured (SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY)" in caplog.text

def test_warn_startup_profile_cloud_no_sandbox(mocker, caplog):
    caplog.set_level(logging.WARNING)
    mocker.patch("koraku.server_core.product_hooks_active", return_value=True)
    mock_supabase_tenant_configured = mocker.MagicMock(return_value=True)
    mocker.patch.dict("sys.modules", {
        "koraku_cloud.integrations.supabase_tenant": mocker.MagicMock(
            supabase_tenant_configured=mock_supabase_tenant_configured
        )
    })

    configure(default_execution_target="cloud", blaxel_cloud_sandbox_enabled=False)

    warn_startup_profile()
    assert "Cloud execution requires Blaxel (BLAXEL_CLOUD_SANDBOX_ENABLED=true, BL_WORKSPACE, BL_API_KEY)" in caplog.text

def test_warn_startup_profile_all_configured(mocker, caplog):
    caplog.set_level(logging.WARNING)
    mocker.patch("koraku.server_core.product_hooks_active", return_value=True)
    mock_supabase_tenant_configured = mocker.MagicMock(return_value=True)
    mocker.patch.dict("sys.modules", {
        "koraku_cloud.integrations.supabase_tenant": mocker.MagicMock(
            supabase_tenant_configured=mock_supabase_tenant_configured
        )
    })

    configure(default_execution_target="local", blaxel_cloud_sandbox_enabled=True)

    caplog.clear()
    warn_startup_profile()
    assert not caplog.records
