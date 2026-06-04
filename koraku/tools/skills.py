"""Discover modular Koraku skills from the workspace (.koraku/skills/*/SKILL.md)."""
from __future__ import annotations

from pathlib import Path

_skill_catalog_cache: dict[str, tuple[float, str]] = {}


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


def _skills_tree_max_mtime(root: Path) -> float:
    if not root.is_dir():
        return 0.0
    latest = 0.0
    bundled = bundled_skill_roots()
    try:
        latest = max(latest, bundled.stat().st_mtime)
    except OSError:
        pass
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
    max_total_chars: int = 14_000,
    per_skill_cap: int = 6_000,
) -> str:
    root = skill_roots(workspace)
    workspace_slugs: set[str] = set()
    chunks: list[str] = []
    total = 0

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

    return "## Loaded workspace skills\n" + "".join(chunks)


def load_skill_catalog(workspace: str, max_total_chars: int = 14_000, per_skill_cap: int = 6_000) -> str:
    """Return markdown-ish text listing skills and trimmed SKILL.md bodies for the system prompt."""
    ws = str(Path(workspace).resolve())
    root = skill_roots(ws)
    stamp = _skills_tree_max_mtime(root)
    cached = _skill_catalog_cache.get(ws)
    if cached is not None and cached[0] == stamp:
        return cached[1]
    text = _load_skill_catalog_uncached(ws, max_total_chars, per_skill_cap)
    _skill_catalog_cache[ws] = (stamp, text)
    return text
