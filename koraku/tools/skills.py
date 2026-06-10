"""Discover Koraku skills — Supabase (cloud) or workspace ``.koraku/skills/`` (SDK)."""
from __future__ import annotations

import re
from contextvars import ContextVar, Token
from pathlib import Path
from typing import TypedDict

from koraku.core.config import settings
from koraku.core.product_hooks import product_hooks_active
from koraku.tools.tool_def import Tool

_skill_catalog_cache: dict[str, tuple[float, str]] = {}
_active_org_skills: ContextVar[list["CloudSkill"] | None] = ContextVar("koraku_org_skills", default=None)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


class CloudSkill(TypedDict):
    slug: str
    name: str
    description: str
    body: str


def bind_org_skills(skills: list[CloudSkill] | None) -> Token[list[CloudSkill] | None]:
    rows = [dict(skill) for skill in (skills or [])] if skills else None
    return _active_org_skills.set(rows)  # type: ignore[arg-type]


def reset_org_skills(token: Token[list[CloudSkill] | None]) -> None:
    _active_org_skills.reset(token)


def get_bound_org_skills() -> list[CloudSkill]:
    raw = _active_org_skills.get()
    if not raw:
        return []
    return [dict(row) for row in raw if isinstance(row, dict)]


def skill_roots(workspace: str) -> Path:
    return Path(workspace).resolve() / ".koraku" / "skills"


def bundled_skill_roots() -> Path:
    return Path(__file__).resolve().parent.parent / "artifacts" / "default_skills"


def _parse_description_from_body(body: str) -> str:
    text = body or ""
    match = _FRONTMATTER_RE.match(text)
    if match:
        block = match.group(1)
        for line in block.splitlines():
            if line.strip().lower().startswith("description:"):
                return line.split(":", 1)[1].strip()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped[:240]
    return ""


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


def _skill_index_line(*, slug: str, name: str, description: str, source: str) -> str:
    label = (name or slug).strip()
    desc = (description or "No description").strip()
    return f"- `{slug}` — **{label}** ({source}): {desc}"


def _bundled_skill_index_lines() -> list[str]:
    root = bundled_skill_roots()
    if not root.is_dir():
        return []
    lines: list[str] = []
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
        desc = _parse_description_from_body(body)
        lines.append(_skill_index_line(slug=slug, name=slug, description=desc, source="bundled"))
    return lines


def _cloud_skill_index_lines(skills: list[CloudSkill]) -> list[str]:
    lines: list[str] = []
    for skill in skills:
        slug = (skill.get("slug") or "").strip()
        if not slug:
            continue
        name = (skill.get("name") or slug).strip()
        desc = (skill.get("description") or "").strip() or _parse_description_from_body(skill.get("body") or "")
        lines.append(_skill_index_line(slug=slug, name=name, description=desc, source="org"))
    return lines


def _workspace_skill_index_lines(workspace: str) -> list[str]:
    root = skill_roots(workspace)
    if not root.is_dir():
        return []
    lines: list[str] = []
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
        desc = _parse_description_from_body(body)
        lines.append(_skill_index_line(slug=slug, name=slug, description=desc, source="workspace"))
    return lines


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


def _load_skill_index_uncached(
    workspace: str,
    *,
    cloud_skills: list[CloudSkill] | None = None,
) -> str:
    cloud_mode = product_hooks_active()
    lines: list[str] = []
    org_slugs: set[str] = set()

    if cloud_mode:
        for line in _cloud_skill_index_lines(cloud_skills or []):
            lines.append(line)
            slug = line.split("`")[1] if "`" in line else ""
            if slug:
                org_slugs.add(slug)
    else:
        lines.extend(_workspace_skill_index_lines(workspace))

    for line in _bundled_skill_index_lines():
        slug = line.split("`")[1] if "`" in line else ""
        if slug and slug in org_slugs:
            continue
        lines.append(line)

    if not lines:
        return ""

    header = (
        "## Agent skills (index)\n"
        "When a task matches a skill, call **SkillLoad** with its slug before following the playbook. "
        "Bundled platform skills are listed below.\n\n"
    )
    return header + "\n".join(lines) + "\n"


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


def load_skill_prompt_section(
    workspace: str,
    *,
    cloud_skills: list[CloudSkill] | None = None,
) -> str:
    """Skills section for the system prompt (index in cloud, full catalog in SDK)."""
    ws = str(Path(workspace).resolve())
    root = skill_roots(ws)
    include_workspace = not product_hooks_active()
    stamp = _skills_tree_max_mtime(root, include_workspace=include_workspace)
    if cloud_skills:
        stamp = max(stamp, float(len(cloud_skills)))
    cache_key = _catalog_cache_key(ws, cloud_skills)
    mode = "index" if product_hooks_active() else "full"
    cache_key = f"{mode}:{cache_key}"
    cached = _skill_catalog_cache.get(cache_key)
    if cached is not None and cached[0] == stamp:
        return cached[1]
    if product_hooks_active():
        text = _load_skill_index_uncached(ws, cloud_skills=cloud_skills)
    else:
        text = _load_skill_catalog_uncached(ws, cloud_skills=cloud_skills)
    _skill_catalog_cache[cache_key] = (stamp, text)
    return text


def load_skill_catalog(
    workspace: str,
    max_total_chars: int | None = None,
    per_skill_cap: int | None = None,
    *,
    cloud_skills: list[CloudSkill] | None = None,
) -> str:
    """Return markdown listing full skill bodies (SDK / legacy)."""
    ws = str(Path(workspace).resolve())
    root = skill_roots(ws)
    include_workspace = not product_hooks_active()
    stamp = _skills_tree_max_mtime(root, include_workspace=include_workspace)
    if cloud_skills:
        stamp = max(stamp, float(len(cloud_skills)))
    cache_key = f"full:{_catalog_cache_key(ws, cloud_skills)}"
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


def resolve_skill_body(
    slug: str,
    workspace: str,
    *,
    cloud_skills: list[CloudSkill] | None = None,
) -> str | None:
    """Load full skill markdown by slug (org, workspace, or bundled)."""
    normalized = (slug or "").strip().lower()
    if not normalized:
        return None

    org_rows = cloud_skills if cloud_skills is not None else get_bound_org_skills()
    for skill in org_rows:
        if (skill.get("slug") or "").strip().lower() == normalized:
            body = (skill.get("body") or "").strip()
            if body:
                name = (skill.get("name") or normalized).strip()
                desc = (skill.get("description") or "").strip()
                if desc and desc not in body[:200]:
                    return f"---\ndescription: {desc}\nname: {name}\n---\n\n{body}"
                return body

    if not product_hooks_active():
        ws_skill = skill_roots(workspace) / normalized / "SKILL.md"
        if ws_skill.is_file():
            try:
                return ws_skill.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass

    bundled_skill = bundled_skill_roots() / normalized / "SKILL.md"
    if bundled_skill.is_file():
        try:
            return bundled_skill.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
    return None


async def _skill_load_handler(slug: str) -> str:
    from koraku.workspace.agent_workspace import get_active_agent_workspace

    ws = get_active_agent_workspace() or str(Path.cwd())
    body = resolve_skill_body(slug, ws)
    if not body:
        return f"Error: No skill found for slug {slug!r}. Use an slug from the skills index."
    cap = int(settings.skill_catalog_per_skill_max_chars)
    if len(body) > cap:
        body = body[:cap] + "\n\n[... skill truncated for context ...]"
    return f"## Skill `{slug.strip().lower()}`\n\n{body}"


skill_load_tool = Tool(
    name="SkillLoad",
    description=(
        "Load the full instructions for a skill slug from the skills index. "
        "Call this when the user's task matches a listed skill before executing steps."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "slug": {
                "type": "string",
                "description": "Skill slug from the skills index (e.g. pdf-worker, weekly-plan).",
            },
        },
        "required": ["slug"],
    },
    handler=_skill_load_handler,
    categories=["skills"],
)


def skills_empty_message() -> str:
    if product_hooks_active():
        bundled = _bundled_skill_index_lines()
        if bundled:
            return (
                "## Agent skills\n"
                "No custom org skills yet. Bundled platform skills still apply — use **SkillLoad** "
                "with a slug from the index when relevant.\n"
            )
        return (
            "## Agent skills\n"
            "No custom org skills yet. Add skills in Settings → Skills.\n"
        )
    return "## Workspace skills\nNo SKILL.md under `.koraku/skills/` yet.\n"
