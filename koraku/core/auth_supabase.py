"""Verify Supabase-issued JWTs for per-user backend features (e.g. Composio).

Supports:

- **HS256** with ``SUPABASE_JWT_SECRET`` (legacy / shared-secret projects).
- **ES256 / RS256 / ES384 / PS256** via the project JWKS URL derived from the token ``iss``
  (asymmetric signing; no shared secret required on the backend).
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlparse

import jwt
from jwt import PyJWKClient

from koraku.core.config import settings

logger = logging.getLogger(__name__)

_ASYMMETRIC_ALGS = frozenset({"ES256", "RS256", "ES384", "PS256"})


def supabase_jwt_secret() -> str:
    return (settings.supabase_jwt_secret or os.environ.get("SUPABASE_JWT_SECRET", "") or "").strip()


@dataclass(frozen=True)
class SupabaseJwtResult:
    """Outcome of verifying a Supabase access token (never includes the raw token)."""

    sub: str | None
    reason: str

    @property
    def ok(self) -> bool:
        return self.sub is not None


SUPABASE_JWT_REQUEST_ERROR_MESSAGES: dict[str, str] = {
    "no_secret": (
        "This token is HS256 but SUPABASE_JWT_SECRET is not set on the backend. "
        "Add it from Supabase → Settings → API (JWT Secret), or use asymmetric (ES256) tokens."
    ),
    "no_header": "Missing Authorization header (Next.js proxy should attach Bearer from Supabase cookies).",
    "bad_scheme": "Authorization must be Bearer <Supabase access_token>.",
    "empty_token": "Bearer token was empty.",
    "unsupported_alg": "JWT signing algorithm is not supported by Koraku.",
    "invalid_issuer": "JWT issuer (iss) is not a trusted Supabase host (*.supabase.co).",
    "expired": "Supabase session expired; sign in again from the web app.",
    "invalid_token": (
        "Invalid Supabase JWT — ensure the web app and backend use the same Supabase project; "
        "for HS256 set SUPABASE_JWT_SECRET; for ES256/RS256 JWKS is fetched from the token iss."
    ),
}


def _iss_to_jwks_url(iss: str) -> str | None:
    """Build JWKS URL from Supabase ``iss``; restrict hosts to reduce SSRF."""
    s = iss.strip().rstrip("/")
    if not s.lower().startswith("https://"):
        return None
    try:
        host = (urlparse(s).hostname or "").lower()
    except ValueError:
        return None
    if not host.endswith(".supabase.co"):
        return None
    return f"{s}/.well-known/jwks.json"


@lru_cache(maxsize=8)
def _jwks_client(url: str) -> PyJWKClient:
    return PyJWKClient(url, cache_keys=True)


def _decode_with_audience_fallback(
    token: str,
    key: object,
    algorithms: list[str],
) -> dict:
    try:
        return jwt.decode(
            token,
            key,
            algorithms=algorithms,
            audience="authenticated",
            leeway=45,
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise
    except jwt.InvalidAudienceError:
        payload = jwt.decode(
            token,
            key,
            algorithms=algorithms,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": False,
                "require": ["exp", "sub"],
            },
            leeway=45,
        )
        role = payload.get("role")
        if role != "authenticated":
            raise jwt.InvalidTokenError("role not authenticated")
        return payload


def _verify_hs256(token: str, secret: str) -> SupabaseJwtResult:
    try:
        payload = _decode_with_audience_fallback(token, secret, ["HS256"])
    except jwt.ExpiredSignatureError:
        return SupabaseJwtResult(None, "expired")
    except jwt.PyJWTError:
        return SupabaseJwtResult(None, "invalid_token")
    sub = payload.get("sub")
    if isinstance(sub, str) and sub.strip():
        return SupabaseJwtResult(sub.strip(), "ok")
    return SupabaseJwtResult(None, "invalid_token")


def _verify_asymmetric(token: str, alg: str) -> SupabaseJwtResult:
    try:
        unverified = jwt.decode(token, options={"verify_signature": False})
    except jwt.PyJWTError:
        return SupabaseJwtResult(None, "invalid_token")
    iss = unverified.get("iss")
    if not isinstance(iss, str) or not iss.strip():
        return SupabaseJwtResult(None, "invalid_issuer")
    jwks_url = _iss_to_jwks_url(iss.strip())
    if not jwks_url:
        return SupabaseJwtResult(None, "invalid_issuer")
    try:
        signing_key = _jwks_client(jwks_url).get_signing_key_from_jwt(token)
        payload = _decode_with_audience_fallback(token, signing_key.key, [alg])
    except jwt.ExpiredSignatureError:
        return SupabaseJwtResult(None, "expired")
    except jwt.PyJWTError as e:
        logger.debug("JWT asymmetric verify failed: %s", e)
        return SupabaseJwtResult(None, "invalid_token")
    sub = payload.get("sub")
    if isinstance(sub, str) and sub.strip():
        return SupabaseJwtResult(sub.strip(), "ok")
    return SupabaseJwtResult(None, "invalid_token")


def verify_supabase_jwt_bearer_detail(authorization: str | None) -> SupabaseJwtResult:
    """Return ``sub`` and a stable ``reason`` for logging / HTTP errors."""
    if not authorization or not str(authorization).strip():
        return SupabaseJwtResult(None, "no_header")
    raw = str(authorization).strip()
    if not raw.lower().startswith("bearer "):
        return SupabaseJwtResult(None, "bad_scheme")
    token = raw[7:].strip().split()[0] if raw[7:].strip() else ""
    if not token:
        return SupabaseJwtResult(None, "empty_token")

    try:
        hdr = jwt.get_unverified_header(token)
        alg = (hdr.get("alg") or "").upper()
    except jwt.PyJWTError:
        return SupabaseJwtResult(None, "invalid_token")

    secret = supabase_jwt_secret()

    if alg == "HS256":
        if not secret:
            return SupabaseJwtResult(None, "no_secret")
        return _verify_hs256(token, secret)

    if alg in _ASYMMETRIC_ALGS:
        return _verify_asymmetric(token, alg)

    logger.warning("Unsupported Supabase JWT alg: %s", alg or "?")
    return SupabaseJwtResult(None, "unsupported_alg")
