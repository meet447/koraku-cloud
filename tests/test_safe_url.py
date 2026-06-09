"""Safe public URL validation."""
from __future__ import annotations

import pytest

from koraku.integrations.safe_url import assert_public_fetch_url, normalize_public_url


def test_normalize_public_url_adds_https() -> None:
    assert normalize_public_url("example.com/about") == "https://example.com/about"


def test_normalize_public_url_rejects_localhost() -> None:
    assert normalize_public_url("http://localhost:8000") is None


def test_assert_public_fetch_url_rejects_private_literal_ip() -> None:
    with pytest.raises(ValueError, match="not allowed|private"):
        assert_public_fetch_url("http://127.0.0.1/secret")
