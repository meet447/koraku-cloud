"""Best-effort redaction of secrets before logging or support exports."""
from __future__ import annotations

import itertools
import json
import re
from typing import Any

_JWT = re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
_BEARER = re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+", re.I)
_APIISH = re.compile(r"\b(sk|rk|pk|xox[baprs]-)[A-Za-z0-9_-]{12,}\b", re.I)
_HEX_RUN = re.compile(r"\b[0-9a-f]{32,}\b", re.I)

_PLACEHOLDER = "[REDACTED]"

_SENSITIVE_KEY = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "api_key",
        "apikey",
        "authorization",
        "access_token",
        "refresh_token",
        "id_token",
        "token",
        "client_secret",
        "private_key",
        "supabase_service_role_key",
        "anthropic_api_key",
        "openai_api_key",
    }
)


def redact_secrets(text: str, *, placeholder: str = _PLACEHOLDER) -> str:
    """Redact common token patterns from a single string (logs, error messages)."""
    if not text:
        return text
    s = _BEARER.sub(f"Bearer {placeholder}", text)
    s = _JWT.sub(placeholder, s)
    s = _APIISH.sub(placeholder, s)
    s = _HEX_RUN.sub(placeholder, s)
    return s


def redact_mapping(obj: Any, *, max_depth: int = 6, _depth: int = 0) -> Any:
    """Return a JSON-safe structure with sensitive keys and long strings scrubbed."""
    if _depth > max_depth:
        return "[TRUNCATED]"
    if obj is None or isinstance(obj, (bool, int, float)):
        return obj
    if isinstance(obj, str):
        return redact_secrets(obj)
    if isinstance(obj, list):
        return [redact_mapping(x, max_depth=max_depth, _depth=_depth + 1) for x in itertools.islice(obj, 200)]
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in itertools.islice(obj.items(), 200):
            lk = str(k).lower()
            if lk in _SENSITIVE_KEY:
                out[str(k)] = _PLACEHOLDER
            else:
                out[str(k)] = redact_mapping(v, max_depth=max_depth, _depth=_depth + 1)
        return out
    try:
        return redact_secrets(json.dumps(obj, default=str))[:2000]
    except (TypeError, ValueError):
        return _PLACEHOLDER
