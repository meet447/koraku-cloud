from __future__ import annotations

import pytest
from pytest_mock import MockerFixture

from koraku.server_core import run_startup_checks


def test_run_startup_checks_orchestration(mocker: MockerFixture) -> None:
    m_workspace = mocker.patch("koraku.server_core.assert_workspace_safe")
    m_resolve = mocker.patch("koraku.server_core.resolve_server_mode")
    m_cors = mocker.patch("koraku.server_core.assert_cors_safe")
    m_warn = mocker.patch("koraku.server_core.warn_startup_profile")
    m_redis = mocker.patch("koraku.server_core.assert_redis_for_multi_worker")

    m_resolve.return_value = ("mock_agent", "mock_mode")

    agent, mode = run_startup_checks()

    assert agent == "mock_agent"
    assert mode == "mock_mode"

    m_workspace.assert_called_once()
    m_resolve.assert_called_once()
    m_cors.assert_called_once_with("mock_mode")
    m_warn.assert_called_once()
    m_redis.assert_called_once()


def test_run_startup_checks_propagates_errors(mocker: MockerFixture) -> None:
    mocker.patch(
        "koraku.server_core.assert_workspace_safe", side_effect=RuntimeError("Workspace unsafe")
    )
    m_resolve = mocker.patch("koraku.server_core.resolve_server_mode")

    with pytest.raises(RuntimeError, match="Workspace unsafe"):
        run_startup_checks()

    m_resolve.assert_not_called()

import logging
from koraku.core.config import use_settings
from koraku.core.sdk_settings import SdkSettings
from koraku.server_core import assert_cors_safe

def test_assert_cors_safe_not_live(caplog: pytest.LogCaptureFixture) -> None:
    """It does nothing if mode is not 'live', even if origin is *."""
    with use_settings(SdkSettings(cors_allowed_origins="*")):
        with caplog.at_level(logging.WARNING):
            assert_cors_safe("unconfigured")
        assert not caplog.records

def test_assert_cors_safe_empty_origins(caplog: pytest.LogCaptureFixture) -> None:
    """It logs a warning if mode is 'live' and no origins are specified."""
    with use_settings(SdkSettings(cors_allowed_origins="")):
        with caplog.at_level(logging.WARNING):
            assert_cors_safe("live")
        assert len(caplog.records) == 1
        assert "CORS_ALLOWED_ORIGINS is empty" in caplog.records[0].message

def test_assert_cors_safe_valid_origins(caplog: pytest.LogCaptureFixture) -> None:
    """It does nothing if mode is 'live' and origins are explicit."""
    with use_settings(SdkSettings(cors_allowed_origins="https://app.example.com")):
        with caplog.at_level(logging.WARNING):
            assert_cors_safe("live")
        assert not caplog.records

def test_assert_cors_safe_star_origin() -> None:
    """It raises RuntimeError if mode is 'live' and origin is *."""
    with use_settings(SdkSettings(cors_allowed_origins="*")):
        with pytest.raises(RuntimeError, match="Refusing to start in live mode with CORS_ALLOWED_ORIGINS='*'"):
            assert_cors_safe("live")

def test_assert_cors_safe_star_origin_with_spaces() -> None:
    """It raises RuntimeError if mode is 'live' and origin is * with spaces."""
    with use_settings(SdkSettings(cors_allowed_origins=" * ")):
        with pytest.raises(RuntimeError, match="Refusing to start in live mode with CORS_ALLOWED_ORIGINS='*'"):
            assert_cors_safe("live")

def test_assert_cors_safe_multiple_with_star_origin() -> None:
    """It raises RuntimeError if mode is 'live' and any origin is *."""
    with use_settings(SdkSettings(cors_allowed_origins="https://app.example.com,*")):
        with pytest.raises(RuntimeError, match="Refusing to start in live mode with CORS_ALLOWED_ORIGINS='*'"):
            assert_cors_safe("live")
