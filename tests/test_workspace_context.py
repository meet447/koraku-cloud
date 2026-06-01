import json
import pytest
from pathlib import Path

from koraku.workspace.context import (
    koraku_dir,
    memory_path,
    legacy_memory_path,
    soul_path,
    personalization_json_path,
    load_memory_snippet,
    load_soul_snippet,
    load_agent_display_name,
    read_personalization_files,
    write_personalization_files,
)

def test_paths(tmp_path: Path) -> None:
    workspace = str(tmp_path)
    kd = koraku_dir(workspace)
    assert kd == tmp_path / ".koraku"
    assert memory_path(workspace) == kd / "Memory.md"
    assert legacy_memory_path(workspace) == kd / "memory.md"
    assert soul_path(workspace) == kd / "Soul.md"
    assert personalization_json_path(workspace) == kd / "personalization.json"

def test_write_and_read_personalization_files(tmp_path: Path) -> None:
    workspace = str(tmp_path)
    write_personalization_files(workspace, " Test Agent  ", "Memory Content", "Soul Content")

    res = read_personalization_files(workspace)
    assert res == {
        "agent_name": "Test Agent",
        "memory": "Memory Content",
        "soul": "Soul Content"
    }

def test_read_personalization_legacy_memory(tmp_path: Path) -> None:
    workspace = str(tmp_path)
    # create only legacy memory
    kd = koraku_dir(workspace)
    kd.mkdir(parents=True, exist_ok=True)
    legacy_memory_path(workspace).write_text("Legacy Memory", encoding="utf-8")

    res = read_personalization_files(workspace)
    assert res["memory"] == "Legacy Memory"

def test_read_personalization_missing_files(tmp_path: Path) -> None:
    workspace = str(tmp_path)
    res = read_personalization_files(workspace)
    assert res == {
        "agent_name": "",
        "memory": "",
        "soul": ""
    }

def test_load_memory_snippet(tmp_path: Path) -> None:
    workspace = str(tmp_path)
    kd = koraku_dir(workspace)
    kd.mkdir(parents=True, exist_ok=True)

    assert load_memory_snippet(workspace) == ""

    legacy_memory_path(workspace).write_text("Legacy", encoding="utf-8")
    assert load_memory_snippet(workspace) == "Legacy"

    # Primary takes precedence
    memory_path(workspace).write_text("Primary", encoding="utf-8")
    assert load_memory_snippet(workspace) == "Primary"

def test_load_memory_snippet_truncation(tmp_path: Path) -> None:
    workspace = str(tmp_path)
    kd = koraku_dir(workspace)
    kd.mkdir(parents=True, exist_ok=True)

    memory_path(workspace).write_text("1234567890", encoding="utf-8")

    res = load_memory_snippet(workspace, max_chars=5)
    assert res == "12345\n\n[... Memory.md truncated ...]"

    legacy_memory_path(workspace).write_text("1234567890", encoding="utf-8")
    memory_path(workspace).unlink()
    if not legacy_memory_path(workspace).exists():
        # Case-insensitive filesystems treat Memory.md and memory.md as the same file.
        return
    res2 = load_memory_snippet(workspace, max_chars=5)
    assert res2 == "12345\n\n[... memory.md truncated ...]"


def test_load_soul_snippet(tmp_path: Path) -> None:
    workspace = str(tmp_path)
    kd = koraku_dir(workspace)
    kd.mkdir(parents=True, exist_ok=True)

    assert load_soul_snippet(workspace) == ""

    soul_path(workspace).write_text("Soul Content", encoding="utf-8")
    assert load_soul_snippet(workspace) == "Soul Content"

    soul_path(workspace).write_text("1234567890", encoding="utf-8")
    res = load_soul_snippet(workspace, max_chars=5)
    assert res == "12345\n\n[... Soul.md truncated ...]"

def test_load_agent_display_name_edge_cases(tmp_path: Path) -> None:
    workspace = str(tmp_path)
    kd = koraku_dir(workspace)
    kd.mkdir(parents=True, exist_ok=True)

    assert load_agent_display_name(workspace) is None

    p = personalization_json_path(workspace)

    # Invalid JSON
    p.write_text("invalid json", encoding="utf-8")
    assert load_agent_display_name(workspace) is None

    # Non-dict
    p.write_text('["list"]', encoding="utf-8")
    assert load_agent_display_name(workspace) is None

    # Missing key
    p.write_text('{"other": 1}', encoding="utf-8")
    assert load_agent_display_name(workspace) is None

    # Empty string
    p.write_text('{"agent_name": "   "}', encoding="utf-8")
    assert load_agent_display_name(workspace) is None

    # Valid
    p.write_text('{"agent_name": "valid_name"}', encoding="utf-8")
    assert load_agent_display_name(workspace) == "valid_name"

    # Truncation
    long_name = "a" * 150
    p.write_text(json.dumps({"agent_name": long_name}), encoding="utf-8")
    assert load_agent_display_name(workspace) == "a" * 120

def test_read_file_oserror(tmp_path: Path, monkeypatch) -> None:
    workspace = str(tmp_path)
    kd = koraku_dir(workspace)
    kd.mkdir(parents=True, exist_ok=True)

    memory_path(workspace).write_text("content", encoding="utf-8")
    soul_path(workspace).write_text("content", encoding="utf-8")

    def mock_read_text(*args, **kwargs):
        raise OSError("denied")

    monkeypatch.setattr(Path, "read_text", mock_read_text)

    assert load_memory_snippet(workspace) == ""
    assert load_soul_snippet(workspace) == ""

    res = read_personalization_files(workspace)
    assert res == {
        "agent_name": "",
        "memory": "",
        "soul": ""
    }
