"""Constant-time comparison for static secrets and token hashes."""
from __future__ import annotations

import hashlib
import hmac
import secrets


def secrets_equal(expected: str, provided: str) -> bool:
    """Compare two strings without leaking length via early exit."""
    a = (expected or "").strip()
    b = (provided or "").strip()
    if not a or not b:
        return False
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def sha256_hex_equal(expected_hex: str, token: str) -> bool:
    """Compare a stored SHA-256 hex digest to ``hashlib.sha256(token)``."""
    stored = (expected_hex or "").strip()
    if not stored or not (token or "").strip():
        return False
    digest = hashlib.sha256(token.strip().encode("utf-8")).hexdigest()
    return secrets.compare_digest(digest, stored)
