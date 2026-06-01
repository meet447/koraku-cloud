"""Workspace API path containment."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from koraku.api.workspace_routes import safe_join_under_session_root


def test_safe_join_root_only() -> None:
    r = "/tmp/koraku/users/u/sessions/sid"
    assert safe_join_under_session_root(r, "") == r


def test_safe_join_nested() -> None:
    r = "/tmp/koraku/users/u/sessions/sid"
    assert safe_join_under_session_root(r, "src") == f"{r}/src"
    assert safe_join_under_session_root(r, "src/a.ts") == f"{r}/src/a.ts"


def test_safe_join_rejects_escape() -> None:
    r = "/tmp/koraku/users/u/sessions/sid"
    with pytest.raises(HTTPException) as exc:
        safe_join_under_session_root(r, "../../../etc/passwd")
    assert exc.value.status_code == 400
