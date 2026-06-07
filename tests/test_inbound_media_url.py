"""SSRF guards for inbound SendBlue media URLs."""
from __future__ import annotations

import pytest

from koraku.integrations.inbound_media_url import validate_inbound_media_url, validate_redirect_url


def test_allows_sendblue_host() -> None:
    assert (
        validate_inbound_media_url("https://storage.sendblue.co/attachments/voice.caf")
        is not None
    )


def test_blocks_http() -> None:
    assert validate_inbound_media_url("http://storage.sendblue.co/x.caf") is None


def test_blocks_localhost() -> None:
    assert validate_inbound_media_url("https://localhost/secret") is None


def test_blocks_private_ip_literal() -> None:
    assert validate_inbound_media_url("https://127.0.0.1/x.caf") is None
    assert validate_inbound_media_url("https://10.0.0.5/x.caf") is None


def test_blocks_metadata_endpoint() -> None:
    assert validate_inbound_media_url("https://169.254.169.254/latest/meta-data/") is None


def test_blocks_unknown_host(monkeypatch: pytest.MonkeyPatch) -> None:
    from koraku.core.config import settings

    monkeypatch.setattr(settings, "sendblue_inbound_media_host_allowlist", "sendblue.co")
    assert validate_inbound_media_url("https://evil.example.com/x.caf") is None


def test_redirect_allows_sendblue_host() -> None:
    assert (
        validate_redirect_url("https://storage.sendblue.co/attachments/voice.caf")
        is not None
    )


def test_redirect_blocks_http() -> None:
    assert validate_redirect_url("http://storage.sendblue.co/x.caf") is None


def test_redirect_blocks_localhost() -> None:
    assert validate_redirect_url("https://localhost/secret") is None


def test_redirect_blocks_private_ip_literal() -> None:
    assert validate_redirect_url("https://127.0.0.1/x.caf") is None
    assert validate_redirect_url("https://10.0.0.5/x.caf") is None


def test_redirect_blocks_unknown_host(monkeypatch: pytest.MonkeyPatch) -> None:
    from koraku.core.config import settings

    monkeypatch.setattr(settings, "sendblue_inbound_media_host_allowlist", "sendblue.co")
    assert validate_redirect_url("https://evil.example.com/x.caf") is None
