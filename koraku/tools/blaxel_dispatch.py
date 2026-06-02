"""Route Read/Write/Edit/Bash/Glob/Grep to an active Blaxel sandbox when bound."""
from __future__ import annotations

import json
import posixpath

from koraku.agent.blaxel_scope import get_active_blaxel_sandbox, get_active_blaxel_session_root
from koraku.core.config import settings


async def _lazy_cloud_ensure() -> str | None:
    """Provision Blaxel on first file/shell tool when chat deferred upfront VM setup."""
    if not bool(getattr(settings, "blaxel_cloud_sandbox_enabled", False)):
        return None
    if get_active_blaxel_sandbox() is not None:
        return None
    from koraku.integrations.blaxel_lazy import ensure_blaxel_for_file_tool

    if await ensure_blaxel_for_file_tool():
        return None
    return (
        "Error: Cloud file tools need the Blaxel sandbox, which is still starting or unavailable. "
        "Retry in a moment."
    )
from koraku.tools.binary_read_paths import format_binary_read_response, should_use_binary_read_branch


def _sandbox_root_posix() -> str:
    """POSIX cwd / file root: per-chat session dir when set, else Blaxel workdir."""
    session = get_active_blaxel_session_root()
    if session and session.strip():
        return session.strip().replace("\\", "/").rstrip("/")
    wd = (settings.blaxel_sandbox_workdir or "").strip().replace("\\", "/").rstrip("/")
    return wd or "/tmp"


def _to_sandbox_path(file_path: str) -> str:
    """Map Koraku workspace-relative paths to an absolute path inside the VM.

    Uses ``posixpath`` only — ``PurePosixPath.resolve`` does not exist (unlike ``Path.resolve``).
    """
    root = _sandbox_root_posix()
    raw = (file_path or "").strip().replace("\\", "/")
    if not raw:
        return root
    if posixpath.isabs(raw):
        candidate = posixpath.normpath(raw)
    else:
        candidate = posixpath.normpath(posixpath.join(root, raw))
    if root == "/":
        return candidate
    root_prefix = root if root.endswith("/") else root + "/"
    if candidate == root or candidate.startswith(root_prefix):
        return candidate
    return posixpath.join(root, posixpath.basename(raw))


async def blaxel_read_if_active(file_path: str, offset: int, limit: int) -> str | None:
    lazy_err = await _lazy_cloud_ensure()
    if lazy_err:
        return lazy_err
    sb = get_active_blaxel_sandbox()
    if sb is None:
        return None
    path = _to_sandbox_path(file_path)
    if should_use_binary_read_branch(file_path):
        read_bin = getattr(sb.fs, "read_binary", None)
        if read_bin is None:
            return format_binary_read_response(file_path, None)
        try:
            data = await read_bin(path)
        except Exception as e:
            return f"Error (Blaxel read_binary): {e}"
        n = len(data) if isinstance(data, (bytes, bytearray)) else 0
        return format_binary_read_response(file_path, n)
    try:
        text = await sb.fs.read(path)
    except Exception as e:
        return f"Error (Blaxel read): {e}"
    lines = text.splitlines(keepends=True)
    start = max(0, offset - 1)
    end = start + limit
    selected = lines[start:end]
    _line_endings = "\n\r"
    numbered = [f"{i}: {line.rstrip(_line_endings)}" for i, line in enumerate(selected, offset)]
    result = "\n".join(numbered)
    if end < len(lines):
        result += f"\n... ({len(lines) - end} more lines)"
    return result


async def blaxel_write_if_active(file_path: str, content: str) -> str | None:
    lazy_err = await _lazy_cloud_ensure()
    if lazy_err:
        return lazy_err
    sb = get_active_blaxel_sandbox()
    if sb is None:
        return None
    path = _to_sandbox_path(file_path)
    try:
        parent = posixpath.dirname(path)
        if parent and parent not in (".", "/"):
            await sb.fs.mkdir(parent, permissions="0755")
    except Exception:
        pass
    try:
        await sb.fs.write(path, content)
    except Exception as e:
        return f"Error (Blaxel write): {e}"
    from koraku.channels.file_attachments import export_blaxel_file_if_imessage

    await export_blaxel_file_if_imessage(sb, path, file_path)
    return f"Wrote {len(content)} chars to {file_path}"


async def blaxel_edit_if_active(file_path: str, old_string: str, new_string: str) -> str | None:
    lazy_err = await _lazy_cloud_ensure()
    if lazy_err:
        return lazy_err
    sb = get_active_blaxel_sandbox()
    if sb is None:
        return None
    path = _to_sandbox_path(file_path)
    try:
        content = await sb.fs.read(path)
    except Exception as e:
        return f"Error (Blaxel edit read): {e}"
    if old_string not in content:
        return "Error: old_string not found in file."
    updated = content.replace(old_string, new_string, 1)
    try:
        await sb.fs.write(path, updated)
    except Exception as e:
        return f"Error (Blaxel edit): {e}"
    from koraku.channels.file_attachments import export_blaxel_file_if_imessage

    await export_blaxel_file_if_imessage(sb, path, file_path)
    return f"Edited {file_path}"


async def blaxel_bash_if_active(command: str, timeout: int = 30) -> str | None:
    lazy_err = await _lazy_cloud_ensure()
    if lazy_err:
        return lazy_err
    sb = get_active_blaxel_sandbox()
    if sb is None:
        return None
    wd = _sandbox_root_posix()
    try:
        resp = await sb.process.exec(
            {
                "command": command,
                "working_dir": wd,
                "wait_for_completion": True,
                "timeout": int(timeout),
            }
        )
    except Exception as e:
        return f"Error (Blaxel shell): {e}"
    out = getattr(resp, "stdout", "") or ""
    err = getattr(resp, "stderr", "") or ""
    code = getattr(resp, "exit_code", None)
    text = out
    if err.strip():
        text += ("\n[stderr]\n" if text else "") + err
    if code is not None and code != 0:
        text += f"\n[exit code {code}]"
    return text[:8000] if text else f"(no output, exit {code})"


async def blaxel_glob_if_active(pattern: str, path: str = ".") -> str | None:
    lazy_err = await _lazy_cloud_ensure()
    if lazy_err:
        return lazy_err
    sb = get_active_blaxel_sandbox()
    if sb is None:
        return None
    base = _to_sandbox_path(path)
    try:
        fr = await sb.fs.find(base, patterns=[pattern], max_results=30)
    except Exception as e:
        err = str(e).lower()
        if any(
            x in err
            for x in ("no such file", "not found", "does not exist", "directory not found")
        ):
            return json.dumps([], indent=2)
        return f"Error (Blaxel glob): {e}"
    matches: list[str] = []
    for m in getattr(fr, "matches", []) or []:
        p = getattr(m, "path", None) or ""
        if p:
            matches.append(str(p))
    return json.dumps(matches[:30], indent=2)


async def blaxel_grep_if_active(pattern: str, path: str = ".", include: str = "*") -> str | None:
    lazy_err = await _lazy_cloud_ensure()
    if lazy_err:
        return lazy_err
    sb = get_active_blaxel_sandbox()
    if sb is None:
        return None
    base = _to_sandbox_path(path)
    file_pat = None if include in ("*", "**/*") else include
    try:
        res = await sb.fs.grep(
            query=pattern,
            path=base,
            file_pattern=file_pat,
            max_results=100,
        )
    except Exception as e:
        return f"Error (Blaxel grep): {e}"
    lines: list[str] = []
    for m in getattr(res, "matches", []) or []:
        fp = getattr(m, "path", "?")
        ln = getattr(m, "line", "?")
        txt = (getattr(m, "text", "") or "").rstrip()
        lines.append(f"{fp}:{ln}: {txt}")
        if len(lines) >= 100:
            break
    if not lines:
        return "No matches."
    return "\n".join(lines[:100])
