"""File tool path sandboxing — workspace boundary enforcement."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from koraku.tools.registry import _resolve_host_path
from koraku.workspace.agent_workspace import agent_workspace_scope


def test_resolve_host_path_uses_agent_workspace_scope():
    with tempfile.TemporaryDirectory() as repo:
        session = Path(repo) / "session-ws"
        session.mkdir()
        outside = Path(repo) / "outside.py"
        with agent_workspace_scope(str(session)):
            fpath, err = _resolve_host_path("outputs/deck.pptx", parent_for_new_file=True)
            assert err is None
            assert fpath is not None
            assert os.path.commonpath([fpath, str(session.resolve())]) == str(session.resolve())

            _, err_out = _resolve_host_path(str(outside))
            assert err_out is not None
            assert "must stay under workspace" in err_out


def test_absolute_path_under_session_workspace_allowed():
    with tempfile.TemporaryDirectory() as base:
        session = Path(base) / "session"
        session.mkdir()
        target = session / "outputs" / "file.txt"
        with agent_workspace_scope(str(session)):
            fpath, err = _resolve_host_path(str(target), parent_for_new_file=True)
            assert err is None
            assert os.path.realpath(fpath) == os.path.realpath(str(target))
