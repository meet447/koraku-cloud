"""Pluggable auth backends."""
from __future__ import annotations

import pytest

from koraku.core.auth import (
    ApiKeyAuthVerifier,
    NoAuthVerifier,
    auth_error_detail,
    build_auth_verifier,
    reset_auth_verifier,
    verify_request_auth,
)
from koraku.core.config import Settings, configure, use_settings


@pytest.fixture(autouse=True)
def _reset_auth() -> None:
    reset_auth_verifier()
    yield
    reset_auth_verifier()


def test_api_key_verifier_accepts_bearer() -> None:
    v = ApiKeyAuthVerifier("secret-key")
    ok = v.verify("Bearer secret-key")
    assert ok.ok
    assert ok.sub == "api-key"
    bad = v.verify("Bearer wrong")
    assert not bad.ok
    assert bad.reason == "api_key_invalid"


def test_no_auth_verifier_allows_anonymous() -> None:
    v = NoAuthVerifier()
    res = v.verify(None)
    assert res.ok
    assert res.sub is None
    assert res.reason == "ok_anonymous"


def test_build_auth_verifier_from_settings() -> None:
    with use_settings(Settings(auth_backend="api_key", koraku_api_key="k-test")):
        reset_auth_verifier()
        v = build_auth_verifier()
        assert v.verify("Bearer k-test").ok


def test_verify_request_auth_respects_configure() -> None:
    configure(Settings(auth_backend="api_key", koraku_api_key="embed-key"))
    reset_auth_verifier()
    assert verify_request_auth("Bearer embed-key").ok
    assert not verify_request_auth("Bearer nope").ok


def test_auth_error_detail_includes_api_key_reasons() -> None:
    assert "KORAKU_API_KEY" in auth_error_detail("api_key_missing")
