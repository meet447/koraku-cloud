from __future__ import annotations

import json
from typing import Any
import pytest
from koraku.core.redact import redact_secrets, redact_mapping, _PLACEHOLDER

def test_redact_secrets_empty_and_basic() -> None:
    assert redact_secrets("") == ""
    assert redact_secrets("hello world") == "hello world"
    assert redact_secrets(None) is None  # type: ignore

def test_redact_secrets_bearer() -> None:
    assert redact_secrets("Bearer mytoken123") == f"Bearer {_PLACEHOLDER}"
    assert redact_secrets("bearer mytoken123") == f"Bearer {_PLACEHOLDER}"
    assert redact_secrets("BEARER mytoken123") == f"Bearer {_PLACEHOLDER}"
    assert redact_secrets("Bearer token.with.dots-and_chars") == f"Bearer {_PLACEHOLDER}"

def test_redact_secrets_jwt() -> None:
    jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoyNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    assert redact_secrets(jwt) == _PLACEHOLDER
    assert redact_secrets(f"Token is {jwt}") == f"Token is {_PLACEHOLDER}"

def test_redact_secrets_api_keys() -> None:
    keys = [
        "sk-1234567890123456",
        "rk-1234567890123456",
        "pk-1234567890123456",
        "xoxb-123456789012-1234567890123",
        "xoxp-123456789012-1234567890123",
        "xoxr-123456789012-1234567890123",
        "xoxs-123456789012-1234567890123",
        "sk-ant-12345678901234567890123456789012",
    ]
    for key in keys:
        assert redact_secrets(key) == _PLACEHOLDER
        assert redact_secrets(f"My key is {key}") == f"My key is {_PLACEHOLDER}"

def test_redact_secrets_hex_run() -> None:
    hex_32 = "a" * 32
    hex_40 = "b" * 40
    assert redact_secrets(hex_32) == _PLACEHOLDER
    assert redact_secrets(hex_40) == _PLACEHOLDER
    assert redact_secrets("short123") == "short123"

def test_redact_secrets_custom_placeholder() -> None:
    assert redact_secrets("sk-1234567890123456", placeholder="HIDDEN") == "HIDDEN"
    assert redact_secrets("Bearer token", placeholder="HIDDEN") == "Bearer HIDDEN"

def test_redact_mapping_primitives() -> None:
    assert redact_mapping(1) == 1
    assert redact_mapping(1.5) == 1.5
    assert redact_mapping(True) is True
    assert redact_mapping(None) is None

def test_redact_mapping_strings() -> None:
    assert redact_mapping("sk-1234567890123456") == _PLACEHOLDER
    assert redact_mapping("regular string") == "regular string"

def test_redact_mapping_lists() -> None:
    assert redact_mapping(["sk-1234567890123456", "ok"]) == [_PLACEHOLDER, "ok"]

    long_list = ["item"] * 250
    redacted_list = redact_mapping(long_list)
    assert len(redacted_list) == 200
    assert redacted_list == ["item"] * 200

def test_redact_mapping_dicts() -> None:
    d = {
        "password": "secret_password",
        "api_key": "sk-123",
        "public_info": "hello",
        "nested": {
            "token": "secret_token",
            "other": "val"
        }
    }
    expected = {
        "password": _PLACEHOLDER,
        "api_key": _PLACEHOLDER,
        "public_info": "hello",
        "nested": {
            "token": _PLACEHOLDER,
            "other": "val"
        }
    }
    assert redact_mapping(d) == expected

def test_redact_mapping_dict_truncation() -> None:
    long_dict = {f"key_{i}": i for i in range(250)}
    redacted_dict = redact_mapping(long_dict)
    assert len(redacted_dict) == 200

def test_redact_mapping_max_depth() -> None:
    deep_dict = {}
    curr = deep_dict
    for _ in range(10):
        curr["next"] = {}
        curr = curr["next"]

    redacted = redact_mapping(deep_dict)

    # Check that at depth 7 (0-indexed 6 is ok, 7 is truncated) it is truncated
    curr = redacted
    for _ in range(6):
        curr = curr["next"]
    assert curr["next"] == "[TRUNCATED]"

def test_redact_mapping_fallback() -> None:
    class Unserializable:
        def __str__(self):
            return "sk-1234567890123456"

    obj = Unserializable()
    # json.dumps(obj, default=str) will use str(obj) which returns the secret
    # json.dumps will wrap it in quotes: '"sk-12345..."'
    # then redact_secrets should redact it to '"[REDACTED]"'
    assert redact_mapping(obj) == f'"{_PLACEHOLDER}"'


def test_redact_mapping_fallback_truncation() -> None:
    class VeryLong:
        def __str__(self):
            return "z" * 3000  # 'z' is not a hex digit, so it won't be redacted

    obj = VeryLong()
    redacted = redact_mapping(obj)
    assert len(redacted) == 2000
    # json.dumps wraps in quotes, so it starts with "
    assert redacted.startswith('"zzzz')
