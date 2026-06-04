"""Host file tools stay inside the server workspace."""

from __future__ import annotations

import pytest

from koraku.agent.runtime_context import bind_execution_target, reset_execution_target
from koraku.core.config import settings
from koraku.tools.registry import _read, _write, _path_is_under


@pytest.fixture(autouse=True)
def _local_file_tools() -> None:
    settings.blaxel_cloud_sandbox_enabled = False
    tok = bind_execution_target("local")
    yield
    reset_execution_target(tok)


@pytest.mark.asyncio
async def test_read_rejects_path_outside_workspace(tmp_path) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text("secret-ish", encoding="utf-8")

    result = await _read(str(outside))

    assert result.startswith("Error: Path must stay under workspace:")


@pytest.mark.asyncio
async def test_write_rejects_path_outside_workspace(tmp_path) -> None:
    result = await _write(str(tmp_path / "new.txt"), "nope")

    assert result.startswith("Error: Path must stay under workspace:")


def test_path_is_under_value_error() -> None:
    """Test that _path_is_under catches ValueError from os.path.commonpath."""
    # os.path.commonpath raises ValueError when mixing absolute and relative paths
    assert _path_is_under("/foo", "bar") is False
