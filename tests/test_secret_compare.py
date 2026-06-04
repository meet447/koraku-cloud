"""Constant-time secret helpers."""
from __future__ import annotations

from koraku.core.secret_compare import secrets_equal, sha256_hex_equal
from koraku_cloud.automations.webhook_tokens import hash_webhook_token, verify_webhook_token


def test_secrets_equal_rejects_empty() -> None:
    assert not secrets_equal("secret", "")
    assert not secrets_equal("", "secret")


def test_secrets_equal_matches() -> None:
    assert secrets_equal("abc", "abc")
    assert not secrets_equal("abc", "abd")


def test_webhook_token_verify_uses_digest_compare() -> None:
    token = "test-token-value-1234567890"
    stored = hash_webhook_token(token)
    assert verify_webhook_token(token, stored)
    assert not verify_webhook_token(token + "x", stored)


def test_sha256_hex_equal() -> None:
    assert sha256_hex_equal(hash_webhook_token("x"), "x")
