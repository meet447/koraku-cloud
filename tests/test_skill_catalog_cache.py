"""Workspace skill catalog disk cache."""

from __future__ import annotations

import os
from pathlib import Path

from koraku.tools import skills


def test_load_skill_catalog_reuses_cache_until_mtime_changes(tmp_path: Path) -> None:
    skills._skill_catalog_cache.clear()
    root = tmp_path / ".koraku" / "skills" / "demo"
    root.mkdir(parents=True)
    skill_file = root / "SKILL.md"
    skill_file.write_text("version one", encoding="utf-8")

    first = skills.load_skill_catalog(str(tmp_path))
    assert "version one" in first
    second = skills.load_skill_catalog(str(tmp_path))
    assert second == first

    skill_file.write_text("version two", encoding="utf-8")
    import time; time.sleep(0.01); os.utime(skill_file, None)
    third = skills.load_skill_catalog(str(tmp_path))
    assert "version two" in third
    assert "version one" not in third
