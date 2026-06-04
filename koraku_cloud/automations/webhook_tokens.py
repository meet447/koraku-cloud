"""Webhook tokens for event-triggered automations."""
from __future__ import annotations

import hashlib
import secrets

from koraku.core.secret_compare import sha256_hex_equal


def generate_webhook_token() -> str:
    return secrets.token_urlsafe(32)


def hash_webhook_token(token: str) -> str:
    return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()


def verify_webhook_token(token: str, stored_hash: str | None) -> bool:
    return sha256_hex_equal(stored_hash or "", token)
