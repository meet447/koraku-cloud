"""Pluggable request authentication for embedders and self-hosters."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal, Protocol

from koraku.core.auth_supabase import (
    SUPABASE_JWT_REQUEST_ERROR_MESSAGES,
    SupabaseJwtResult,
    verify_supabase_jwt_bearer_detail,
)
from koraku.core.config import get_settings

AuthBackend = Literal["supabase", "api_key", "none"]

AUTH_ERROR_MESSAGES: dict[str, str] = {
    **SUPABASE_JWT_REQUEST_ERROR_MESSAGES,
    "api_key_missing": "Set KORAKU_API_KEY on the server and send Authorization: Bearer <key>.",
    "api_key_invalid": "Invalid API key.",
}


@dataclass(frozen=True)
class AuthResult:
    """Outcome of verifying a request's credentials."""

    sub: str | None
    reason: str

    @property
    def ok(self) -> bool:
        return self.reason in ("ok", "ok_anonymous")


def auth_error_detail(reason: str) -> str:
    return AUTH_ERROR_MESSAGES.get(reason, "Authorization required.")


class AuthVerifier(Protocol):
    def verify(self, authorization: str | None) -> AuthResult: ...


class SupabaseAuthVerifier:
    def verify(self, authorization: str | None) -> AuthResult:
        res: SupabaseJwtResult = verify_supabase_jwt_bearer_detail(authorization)
        if res.ok:
            return AuthResult(sub=res.sub, reason="ok")
        return AuthResult(sub=None, reason=res.reason)


class ApiKeyAuthVerifier:
    """Static bearer token auth for service-to-service or single-tenant embeds."""

    def __init__(self, api_key: str, *, subject: str = "api-key") -> None:
        self._api_key = api_key.strip()
        self._subject = subject

    def verify(self, authorization: str | None) -> AuthResult:
        if not self._api_key:
            return AuthResult(sub=None, reason="api_key_missing")
        if not authorization or not str(authorization).strip():
            return AuthResult(sub=None, reason="no_header")
        raw = str(authorization).strip()
        if not raw.lower().startswith("bearer "):
            return AuthResult(sub=None, reason="bad_scheme")
        token = raw[7:].strip().split()[0] if raw[7:].strip() else ""
        if not token:
            return AuthResult(sub=None, reason="empty_token")
        if token != self._api_key:
            return AuthResult(sub=None, reason="api_key_invalid")
        return AuthResult(sub=self._subject, reason="ok")


class NoAuthVerifier:
    """Allow all requests; ``sub`` is always ``None`` (use with ``REQUIRE_AUTH_FOR_CHAT=false``)."""

    def verify(self, authorization: str | None) -> AuthResult:
        return AuthResult(sub=None, reason="ok_anonymous")


def _resolve_api_key() -> str:
    settings = get_settings()
    return (settings.koraku_api_key or os.environ.get("KORAKU_API_KEY", "") or "").strip()


def build_auth_verifier(backend: AuthBackend | str | None = None) -> AuthVerifier:
    settings = get_settings()
    name = (backend or settings.auth_backend or "supabase").strip().lower()
    if name == "api_key":
        return ApiKeyAuthVerifier(_resolve_api_key())
    if name == "none":
        return NoAuthVerifier()
    return SupabaseAuthVerifier()


_verifier: AuthVerifier | None = None


def get_auth_verifier() -> AuthVerifier:
    global _verifier
    if _verifier is None:
        _verifier = build_auth_verifier()
    return _verifier


def reset_auth_verifier() -> None:
    """Test helper — rebuild verifier from current settings."""
    global _verifier
    _verifier = None


def verify_request_auth(authorization: str | None) -> AuthResult:
    return get_auth_verifier().verify(authorization)


def verify_request_sub(authorization: str | None) -> str | None:
    return verify_request_auth(authorization).sub
