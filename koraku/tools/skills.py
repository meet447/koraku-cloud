"""Discover modular Koraku skills from the workspace (.koraku/skills/*/SKILL.md)."""
from pathlib import Path


def skill_roots(workspace: str) -> Path:
    return Path(workspace).resolve() / ".koraku" / "skills"


def load_skill_catalog(workspace: str, max_total_chars: int = 14_000, per_skill_cap: int = 6_000) -> str:
    """Return markdown-ish text listing skills and trimmed SKILL.md bodies for the system prompt."""
    root = skill_roots(workspace)
    if not root.is_dir():
        return ""

    chunks: list[str] = []
    total = 0
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
        block = f"### Skill: `{slug}`\n{body}\n"
        if total + len(block) > max_total_chars:
            chunks.append("\n[Additional skills omitted to stay within context budget.]\n")
            break
        chunks.append(block)
        total += len(block)

    if not chunks:
        return ""

    return "## Loaded workspace skills\n" + "".join(chunks)
