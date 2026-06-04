"""Shared PostgREST access for Supabase (service role, connection pooling)."""
from __future__ import annotations

import logging
from typing import Any

import httpx

log = logging.getLogger(__name__)


def _settings():
    from koraku.core.config import settings

    return settings

_client: httpx.Client | None = None


def supabase_rest_configured() -> bool:
    settings = _settings()
    u = (settings.supabase_url or "").strip().rstrip("/")
    k = (settings.supabase_service_role_key or "").strip()
    return bool(u and k)


def require_config() -> tuple[str, str]:
    settings = _settings()
    u = (settings.supabase_url or "").strip().rstrip("/")
    k = (settings.supabase_service_role_key or "").strip()
    if not u or not k:
        raise RuntimeError(
            "Supabase requires SUPABASE_URL (or NEXT_PUBLIC_SUPABASE_URL) and "
            "SUPABASE_SERVICE_ROLE_KEY in the Koraku backend environment."
        )
    return u, k


def headers(*, prefer_representation: bool = False) -> dict[str, str]:
    _, key = require_config()
    h = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if prefer_representation:
        h["Prefer"] = "return=representation"
    return h


def rest_url(path: str) -> str:
    base, _ = require_config()
    p = path if path.startswith("/") else f"/{path}"
    return f"{base}/rest/v1{p}"


def get_http_client() -> httpx.Client:
    """Process-wide pooled client for PostgREST (sync API paths)."""
    global _client
    if _client is None:
        _client = httpx.Client(
            timeout=httpx.Timeout(60.0, connect=10.0),
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
        )
    return _client


def reset_http_client() -> None:
    """Test helper — close and drop the pooled client."""
    global _client
    if _client is not None:
        try:
            _client.close()
        except Exception:
            pass
    _client = None
