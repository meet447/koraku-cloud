"""User memory, persona, and workspace paths for Koraku."""
import json
from pathlib import Path


def koraku_dir(workspace: str) -> Path:
    return Path(workspace).resolve() / ".koraku"


def memory_path(workspace: str) -> Path:
    """Canonical preferences file (OpenClaw-style ``Memory.md``)."""
    return koraku_dir(workspace) / "Memory.md"


def legacy_memory_path(workspace: str) -> Path:
    return koraku_dir(workspace) / "memory.md"


def soul_path(workspace: str) -> Path:
    return koraku_dir(workspace) / "Soul.md"


def personalization_json_path(workspace: str) -> Path:
    return koraku_dir(workspace) / "personalization.json"


def _read_file_cap(path: Path, max_chars: int, truncated_note: str) -> str:
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if len(text) > max_chars:
        return text[:max_chars] + truncated_note
    return text


def load_memory_snippet(workspace: str, max_chars: int = 4_000) -> str:
    primary = memory_path(workspace)
    legacy = legacy_memory_path(workspace)
    if primary.is_file():
        return _read_file_cap(primary, max_chars, "\n\n[... Memory.md truncated ...]")
    if legacy.is_file():
        return _read_file_cap(legacy, max_chars, "\n\n[... memory.md truncated ...]")
    return ""


def load_soul_snippet(workspace: str, max_chars: int = 4_000) -> str:
    return _read_file_cap(
        soul_path(workspace),
        max_chars,
        "\n\n[... Soul.md truncated ...]",
    )


def load_agent_display_name(workspace: str) -> str | None:
    p = personalization_json_path(workspace)
    if not p.is_file():
        return None
    try:
        raw = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError, TypeError):
        return None
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("agent_name") or "").strip()
    if not name:
        return None
    return name[:120]


def read_personalization_files(workspace: str) -> dict[str, str]:
    """Full file contents for the personalization API (not truncated)."""
    ws = str(Path(workspace).resolve())
    mem = ""
    mp = memory_path(ws)
    leg = legacy_memory_path(ws)
    if mp.is_file():
        try:
            mem = mp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            mem = ""
    elif leg.is_file():
        try:
            mem = leg.read_text(encoding="utf-8", errors="replace")
        except OSError:
            mem = ""
    soul = ""
    sp = soul_path(ws)
    if sp.is_file():
        try:
            soul = sp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            soul = ""
    name = load_agent_display_name(ws) or ""
    return {"agent_name": name, "memory": mem, "soul": soul}


def write_personalization_files(workspace: str, agent_name: str, memory: str, soul: str) -> None:
    kd = koraku_dir(workspace)
    kd.mkdir(parents=True, exist_ok=True)
    payload = {"agent_name": (agent_name or "").strip()[:120]}
    personalization_json_path(workspace).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    memory_path(workspace).write_text(memory or "", encoding="utf-8")
    soul_path(workspace).write_text(soul or "", encoding="utf-8")
