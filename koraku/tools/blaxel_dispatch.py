"""Route Read/Write/Edit/Bash/Glob/Grep to an active Blaxel sandbox when bound."""
from __future__ import annotations

import json
import posixpath
from collections.abc import Awaitable, Callable
from typing import Any

from koraku.agent.blaxel_scope import get_active_blaxel_sandbox, get_active_blaxel_session_root
from koraku.core.config import settings
from koraku.integrations.blaxel_lazy import cloud_file_tool_block_reason
from koraku.tools.binary_read_paths import format_binary_read_response, should_use_binary_read_branch

SANDBOX_VENV_DIR = ".koraku-venv"

_SANDBOX_PYTHON_PREAMBLE = f"""\
if [ -x {SANDBOX_VENV_DIR}/bin/python ]; then
  export PATH="{SANDBOX_VENV_DIR}/bin:$PATH"
elif [ ! -f {SANDBOX_VENV_DIR}/.bootstrap_attempted ]; then
  mkdir -p {SANDBOX_VENV_DIR}
  touch {SANDBOX_VENV_DIR}/.bootstrap_attempted
  python3 -m venv {SANDBOX_VENV_DIR} 2>/dev/null || true
  if [ -x {SANDBOX_VENV_DIR}/bin/pip ]; then
    {SANDBOX_VENV_DIR}/bin/pip install -q -U pip matplotlib numpy pillow pandas 2>/dev/null \\
      || {SANDBOX_VENV_DIR}/bin/pip install -q -U pip matplotlib numpy pillow pandas --break-system-packages 2>/dev/null \\
      || true
  fi
  [ -x {SANDBOX_VENV_DIR}/bin/python ] && export PATH="{SANDBOX_VENV_DIR}/bin:$PATH"
fi
"""


def format_blaxel_sandbox_execution_guide(session_root: str) -> str:
    """Short sandbox cookbook appended to the per-turn execution environment note."""
    root = session_root.rstrip("/")
    return (
        f"- **Blaxel sandbox** uses folder `{root}`.\n"
        "- **Paths**: relative to that folder (e.g. `chart.py`, `outputs/plot.png`).\n"
        "- **Python / charts**: Bash auto-activates `.koraku-venv` (created on first shell use). "
        "Run scripts with `python script.py` after `pip install` packages inside the venv.\n"
        "- **Large files**: prefer **Write** with `mode=append` in ~4KB chunks, or Bash "
        "`cat <<'EOF' > file.py` … `EOF` when Write args truncate.\n"
        "- **Grep**: `path` is a directory; to search one file use `path='.'` and "
        "`include='filename.py'`, or pass the file path directly (auto-resolved).\n"
    )


async def _run_blaxel_tool(runner: Callable[[Any], Awaitable[str]]) -> str | None:
    """Try lazy Blaxel attach, then run ``runner(sandbox)``; ``None`` if Blaxel is not active."""
    block = await cloud_file_tool_block_reason(try_ensure=True)
    if block:
        return block
    sb = get_active_blaxel_sandbox()
    if sb is None:
        return None
    return await runner(sb)


def _format_numbered_lines(lines: list[str], offset: int, limit: int) -> str:
    start = max(0, offset - 1)
    end = start + limit
    selected = lines[start:end]
    numbered = [f"{i}: {line.rstrip(chr(10) + chr(13))}" for i, line in enumerate(selected, offset)]
    result = "\n".join(numbered)
    if end < len(lines):
        result += f"\n... ({len(lines) - end} more lines)"
    return result


def _sandbox_root_posix() -> str:
    """POSIX cwd / file root: per-chat session dir when set, else Blaxel workdir."""
    session = get_active_blaxel_session_root()
    if session and session.strip():
        return session.strip().replace("\\", "/").rstrip("/")
    wd = (settings.blaxel_sandbox_workdir or "").strip().replace("\\", "/").rstrip("/")
    return wd or "/tmp"


def sandbox_abs_path(file_path: str) -> str:
    """Map a workspace-relative path to an absolute path inside the active session folder."""
    return _to_sandbox_path(file_path)


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


def _resolve_grep_target(path: str, include: str) -> tuple[str, str | None]:
    """Map grep path to a directory + optional file pattern (Blaxel fs.grep expects a directory)."""
    base = _to_sandbox_path(path)
    raw = (path or "").strip().replace("\\", "/")
    file_pat = None if include in ("*", "**/*") else include
    if raw and not raw.endswith("/") and "." in posixpath.basename(base):
        parent = posixpath.dirname(base)
        if parent and parent not in (".", base):
            basename = posixpath.basename(base)
            if file_pat is None:
                file_pat = basename
            return parent, file_pat
    return base, file_pat


def _bash_with_sandbox_env(command: str) -> str:
    """Prepend idempotent venv bootstrap + PATH for sandbox Python workloads."""
    cmd = (command or "").strip()
    return f"{_SANDBOX_PYTHON_PREAMBLE}\n{cmd}"


async def blaxel_read_if_active(file_path: str, offset: int, limit: int) -> str | None:
    async def _read(sb: Any) -> str:
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
        return _format_numbered_lines(text.splitlines(keepends=True), offset, limit)

    return await _run_blaxel_tool(_read)


async def blaxel_write_if_active(
    file_path: str,
    content: str,
    *,
    mode: str = "overwrite",
) -> str | None:
    async def _write(sb: Any) -> str:
        path = _to_sandbox_path(file_path)
        try:
            parent = posixpath.dirname(path)
            if parent and parent not in (".", "/"):
                await sb.fs.mkdir(parent, permissions="0755")
        except Exception:
            pass
        payload = content
        if (mode or "overwrite").strip().lower() == "append":
            try:
                existing = await sb.fs.read(path)
            except Exception:
                existing = ""
            payload = (existing or "") + content
        try:
            await sb.fs.write(path, payload)
        except Exception as e:
            return f"Error (Blaxel write): {e}"
        from koraku.channels.file_attachments import export_blaxel_file_if_imessage

        await export_blaxel_file_if_imessage(sb, path, file_path)
        action = "Appended" if mode == "append" else "Wrote"
        return f"{action} {len(content)} chars to {file_path}"

    return await _run_blaxel_tool(_write)


async def blaxel_edit_if_active(file_path: str, old_string: str, new_string: str) -> str | None:
    async def _edit(sb: Any) -> str:
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

    return await _run_blaxel_tool(_edit)


async def blaxel_bash_if_active(command: str, timeout: int = 30) -> str | None:
    async def _bash(sb: Any) -> str:
        wd = _sandbox_root_posix()
        wrapped = _bash_with_sandbox_env(command)
        try:
            resp = await sb.process.exec(
                {
                    "command": wrapped,
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

    return await _run_blaxel_tool(_bash)


async def blaxel_glob_if_active(pattern: str, path: str = ".") -> str | None:
    async def _glob(sb: Any) -> str:
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

    return await _run_blaxel_tool(_glob)


async def blaxel_grep_if_active(pattern: str, path: str = ".", include: str = "*") -> str | None:
    async def _grep(sb: Any) -> str:
        base, file_pat = _resolve_grep_target(path, include)
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

    return await _run_blaxel_tool(_grep)
