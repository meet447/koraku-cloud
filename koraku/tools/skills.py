"""Discover Koraku skills — Supabase (cloud) or workspace ``.koraku/skills/`` (SDK)."""
from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from koraku.core.config import settings
from koraku.core.product_hooks import product_hooks_active

_skill_catalog_cache: dict[str, tuple[float, str]] = {}


class CloudSkill(TypedDict):
    slug: str
    name: str
    description: str
    body: str


def skill_roots(workspace: str) -> Path:
    return Path(workspace).resolve() / ".koraku" / "skills"


def bundled_skill_roots() -> Path:
    return Path(__file__).resolve().parent.parent / "artifacts" / "default_skills"


def _read_skill_blocks(root: Path, *, per_skill_cap: int, label_prefix: str) -> list[str]:
    if not root.is_dir():
        return []
    blocks: list[str] = []
    for skill_dir in sorted(root.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            continue
        try:
            body = skill_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        slug = skill_dir.name
        if len(body) > per_skill_cap:
            body = body[:per_skill_cap] + "\n\n[... skill file truncated for context ...]"
        blocks.append(f"### {label_prefix} `{slug}`\n{body}\n")
    return blocks


def _cloud_skill_blocks(skills: list[CloudSkill], *, per_skill_cap: int) -> list[str]:
    blocks: list[str] = []
    for skill in skills:
        slug = (skill.get("slug") or "").strip()
        if not slug:
            continue
        header = (skill.get("name") or slug).strip()
        description = (skill.get("description") or "").strip()
        body = skill.get("body") or ""
        if description and description not in body[:200]:
            body = f"---\ndescription: {description}\n---\n\n{body.lstrip()}"
        if len(body) > per_skill_cap:
            body = body[:per_skill_cap] + "\n\n[... skill file truncated for context ...]"
        blocks.append(f"### Org skill `{slug}` — {header}\n{body}\n")
    return blocks


def _skills_tree_max_mtime(root: Path, *, include_workspace: bool) -> float:
    latest = 0.0
    bundled = bundled_skill_roots()
    try:
        latest = max(latest, bundled.stat().st_mtime)
    except OSError:
        pass
    if not include_workspace:
        return latest
    if not root.is_dir():
        return latest
    try:
        latest = max(latest, root.stat().st_mtime)
    except OSError:
        return latest
    for skill_dir in root.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if skill_file.is_file():
            try:
                latest = max(latest, skill_file.stat().st_mtime)
            except OSError:
                continue
    return latest


def _load_skill_catalog_uncached(
    workspace: str,
    max_total_chars: int | None = None,
    per_skill_cap: int | None = None,
    *,
    cloud_skills: list[CloudSkill] | None = None,
) -> str:
    max_total_chars = int(
        max_total_chars if max_total_chars is not None else settings.skill_catalog_total_max_chars
    )
    per_skill_cap = int(
        per_skill_cap if per_skill_cap is not None else settings.skill_catalog_per_skill_max_chars
    )
    cloud_mode = product_hooks_active()
    root = skill_roots(workspace)
    workspace_slugs: set[str] = set()
    chunks: list[str] = []
    total = 0

    if cloud_mode:
        org_blocks = _cloud_skill_blocks(cloud_skills or [], per_skill_cap=per_skill_cap)
        for block in org_blocks:
            slug_line = block.split("\n", 1)[0]
            slug = slug_line.split("`")[1] if "`" in slug_line else ""
            if slug:
                workspace_slugs.add(slug)
            if total + len(block) > max_total_chars:
                chunks.append("\n[Additional skills omitted to stay within context budget.]\n")
                break
            chunks.append(block)
            total += len(block)
    else:
        for block in _read_skill_blocks(root, per_skill_cap=per_skill_cap, label_prefix="Skill"):
            slug_line = block.split("\n", 1)[0]
            slug = slug_line.split("`")[1] if "`" in slug_line else ""
            if slug:
                workspace_slugs.add(slug)
            if total + len(block) > max_total_chars:
                chunks.append("\n[Additional skills omitted to stay within context budget.]\n")
                break
            chunks.append(block)
            total += len(block)

    bundled = bundled_skill_roots()
    for block in _read_skill_blocks(bundled, per_skill_cap=per_skill_cap, label_prefix="Bundled skill"):
        slug_line = block.split("\n", 1)[0]
        slug = slug_line.split("`")[1] if "`" in slug_line else ""
        if slug and slug in workspace_slugs:
            continue
        if total + len(block) > max_total_chars:
            chunks.append("\n[Additional skills omitted to stay within context budget.]\n")
            break
        chunks.append(block)
        total += len(block)

    if not chunks:
        return ""

    header = "## Loaded org skills\n" if cloud_mode else "## Loaded workspace skills\n"
    return header + "".join(chunks)


def _catalog_cache_key(workspace: str, cloud_skills: list[CloudSkill] | None) -> str:
    if not product_hooks_active():
        return str(Path(workspace).resolve())
    slugs = ",".join(
        sorted((skill.get("slug") or "").strip() for skill in (cloud_skills or []) if skill.get("slug"))
    )
    return f"cloud:{slugs}"


def load_skill_catalog(
    workspace: str,
    max_total_chars: int | None = None,
    per_skill_cap: int | None = None,
    *,
    cloud_skills: list[CloudSkill] | None = None,
) -> str:
    """Return markdown listing skills for the system prompt."""
    ws = str(Path(workspace).resolve())
    root = skill_roots(ws)
    include_workspace = not product_hooks_active()
    stamp = _skills_tree_max_mtime(root, include_workspace=include_workspace)
    if cloud_skills:
        stamp = max(stamp, float(len(cloud_skills)))
    cache_key = _catalog_cache_key(ws, cloud_skills)
    cached = _skill_catalog_cache.get(cache_key)
    if cached is not None and cached[0] == stamp:
        return cached[1]
    text = _load_skill_catalog_uncached(
        ws,
        max_total_chars,
        per_skill_cap,
        cloud_skills=cloud_skills,
    )
    _skill_catalog_cache[cache_key] = (stamp, text)
    return text


def skills_empty_message() -> str:
    if product_hooks_active():
        return (
            "## Agent skills\n"
            "No custom org skills yet — bundled platform skills still apply. "
            "Add skills via the Koraku API (`/api/skills`) or Settings (coming soon).\n"
        )
    return "## Workspace skills\nNo SKILL.md under `.koraku/skills/` yet.\n"
