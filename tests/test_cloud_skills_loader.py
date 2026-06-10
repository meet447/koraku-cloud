"""Cloud-first skill catalog and memory backend."""
from __future__ import annotations

from pathlib import Path

import pytest

from koraku.core.config import Settings, bind_cloud_settings, configure_sdk, reset_cloud_binding
from koraku.core.product_hooks import ProductHooks, clear_product_hooks, register_product_hooks
from koraku.core.sdk_settings import SdkSettings
from koraku.inert_cloud_settings import CloudSettings
from koraku.plugins.memory import get_memory_backend, reset_memory_backend_cache
from koraku.plugins.memory.supermemory import SupermemoryBackend
from koraku.tools import skills


@pytest.fixture(autouse=True)
def _reset_hooks() -> None:
    clear_product_hooks()
    skills._skill_catalog_cache.clear()
    reset_memory_backend_cache()
    reset_cloud_binding()
    yield
    clear_product_hooks()
    skills._skill_catalog_cache.clear()
    reset_memory_backend_cache()
    reset_cloud_binding()


def test_cloud_skill_catalog_ignores_workspace_dot_koraku(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    skill_dir = ws / ".koraku" / "skills" / "local-only"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("should not load in cloud", encoding="utf-8")

    register_product_hooks(ProductHooks())
    text = skills.load_skill_prompt_section(
        str(ws),
        cloud_skills=[
            {
                "slug": "weekly-plan",
                "name": "Weekly plan",
                "description": "Plan the week",
                "body": "Use MemorySearch first.",
            }
        ],
    )
    assert "Agent skills (index)" in text
    assert "`weekly-plan`" in text
    assert "Plan the week" in text
    assert "Use MemorySearch first." not in text
    assert "local-only" not in text
    assert "should not load" not in text


def test_sdk_mode_still_reads_workspace_skills(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    skill_dir = ws / ".koraku" / "skills" / "demo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("workspace skill body", encoding="utf-8")

    text = skills.load_skill_catalog(str(ws))
    assert "Skill `demo`" in text
    assert "workspace skill body" in text


def test_cloud_memory_backend_is_supermemory_not_filesystem() -> None:
    configure_sdk(SdkSettings())
    bind_cloud_settings(CloudSettings.model_construct(memory_backend="supermemory"))
    backend = get_memory_backend(Settings(SdkSettings()))
    assert isinstance(backend, SupermemoryBackend)
