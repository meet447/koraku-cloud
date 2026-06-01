"""Blaxel path mapping must not call ``PurePosixPath.resolve`` (not implemented)."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest


@pytest.fixture
def dispatch(monkeypatch: pytest.MonkeyPatch):
    import koraku.tools.blaxel_dispatch as bd

    monkeypatch.setattr(bd, "settings", SimpleNamespace(blaxel_sandbox_workdir="/tmp"))
    monkeypatch.setattr(bd, "get_active_blaxel_session_root", lambda: None)
    return bd


def test_to_sandbox_relative_file(dispatch) -> None:
    assert dispatch._to_sandbox_path("code.txt") == "/tmp/code.txt"


def test_to_sandbox_empty_is_root(dispatch) -> None:
    assert dispatch._to_sandbox_path("") == "/tmp"


def test_to_sandbox_traversal_collapses_to_basename(dispatch) -> None:
    out = dispatch._to_sandbox_path("a/../../../etc/passwd")
    assert out == "/tmp/passwd"


def test_sandbox_root_default_tmp(monkeypatch: pytest.MonkeyPatch) -> None:
    import koraku.tools.blaxel_dispatch as bd

    monkeypatch.setattr(bd, "settings", SimpleNamespace(blaxel_sandbox_workdir=""))
    monkeypatch.setattr(bd, "get_active_blaxel_session_root", lambda: None)
    assert bd._sandbox_root_posix() == "/tmp"


def test_sandbox_root_prefers_session_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    import koraku.tools.blaxel_dispatch as bd

    monkeypatch.setattr(bd, "settings", SimpleNamespace(blaxel_sandbox_workdir="/tmp"))
    monkeypatch.setattr(bd, "get_active_blaxel_session_root", lambda: "/tmp/koraku/users/u1/sessions/sid")
    assert bd._to_sandbox_path("code.txt") == "/tmp/koraku/users/u1/sessions/sid/code.txt"


def test_blaxel_read_binary_pdf_uses_read_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    import koraku.tools.blaxel_dispatch as bd

    calls: list[str] = []

    class FakeFs:
        async def read_binary(self, path: str) -> bytes:
            calls.append(f"binary:{path}")
            return b"%PDF-1.4"

        async def read(self, path: str) -> str:
            calls.append(f"text:{path}")
            return "should-not-use"

    class FakeSb:
        fs = FakeFs()

    monkeypatch.setattr(bd, "settings", SimpleNamespace(blaxel_sandbox_workdir="/tmp"))
    monkeypatch.setattr(bd, "get_active_blaxel_session_root", lambda: None)
    monkeypatch.setattr(bd, "get_active_blaxel_sandbox", lambda: FakeSb())

    out = asyncio.run(bd.blaxel_read_if_active("spec.pdf", 1, 10))
    assert "Binary file" in out
    assert "spec.pdf" in out
    assert len(calls) == 1
    assert calls[0].startswith("binary:")
