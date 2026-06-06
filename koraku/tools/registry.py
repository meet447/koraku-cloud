"""Industry-standard tool definitions with abstracted web tool names.

Web tools are presented generically to the LLM:
- WebSearch: discovers content (internally uses Exa)
- WebFetch: reads pages (Jina Reader first, Exa Contents second, Firecrawl fallback)

The LLM doesn't need to know about Jina, Exa, or Firecrawl — it just searches and fetches.
"""
import asyncio
import glob as pyglob
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from koraku.core.config import settings
from koraku.tools.policy import tool_stdout_indicates_error
from koraku.tools.tool_def import Tool
from koraku.workspace.paths import workspace_dir


# ========================================================================
# CORE FILE TOOLS (always available)
# ========================================================================

def _effective_workspace_root() -> str:
    """Per-turn workspace from ``agent_workspace_scope``, else process cwd."""
    from koraku.workspace.agent_workspace import get_active_agent_workspace

    active = get_active_agent_workspace()
    if active:
        return os.path.realpath(active)
    return os.path.realpath(workspace_dir())


def _workspace_realpath() -> str:
    return _effective_workspace_root()


def _path_is_under(path: str, root: str) -> bool:
    try:
        return os.path.commonpath([os.path.realpath(path), root]) == root
    except ValueError:
        return False


async def _host_file_tool_block() -> str | None:
    """Block host filesystem tools when cloud mode requires an active Blaxel sandbox."""
    from koraku.integrations.blaxel_lazy import cloud_file_tool_block_reason

    return await cloud_file_tool_block_reason(try_ensure=False)


def _resolve_host_path(path: str, *, parent_for_new_file: bool = False) -> tuple[str | None, str | None]:
    """Resolve a host file-tool path and enforce the workspace boundary when enabled."""
    raw = (path or "").strip()
    if not raw:
        return None, "Error: path is required"
    root = _effective_workspace_root()
    if os.path.isabs(raw):
        fpath = os.path.abspath(os.path.expanduser(raw))
    else:
        fpath = os.path.abspath(os.path.join(root, raw))
    if not settings.host_file_tools_restrict_to_workspace:
        return fpath, None
    check_path = os.path.dirname(fpath) if parent_for_new_file else fpath
    if not _path_is_under(check_path, root):
        return None, f"Error: Path must stay under workspace: {root}"
    return fpath, None

def _read_sync(fpath: str, offset: int, limit: int, file_path: str) -> str:
    from koraku.tools.binary_read_paths import format_binary_read_response, should_use_binary_read_branch
    if not os.path.exists(fpath):
        return f"Error: File not found: {file_path}"
    if should_use_binary_read_branch(fpath):
        try:
            size = os.path.getsize(fpath)
        except OSError as e:
            return f"Error: {e}"
        return format_binary_read_response(file_path, size)
    try:
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        start = max(0, offset - 1)
        end = start + limit
        selected = lines[start:end]
        numbered = [f"{i}: {line}" for i, line in enumerate(selected, start + 1)]
        result = "".join(numbered)
        if end < len(lines):
            result += f"\n... ({len(lines) - end} more lines)"
        return result
    except Exception as e:
        return f"Error: {e}"


async def _read(file_path: str, offset: int = 1, limit: int = 100) -> str:
    """Read a file."""
    from koraku.tools.blaxel_dispatch import blaxel_read_if_active

    bx = await blaxel_read_if_active(file_path, offset, limit)
    if bx is not None:
        return bx
    host_block = await _host_file_tool_block()
    if host_block:
        return host_block

    fpath, path_error = _resolve_host_path(file_path)
    if path_error:
        return path_error
    assert fpath is not None
    return await asyncio.to_thread(_read_sync, fpath, offset, limit, file_path)


read_tool = Tool(
    name="Read",
    description=(
        "Read a text file with line numbers (offset/limit for large files). "
        "For binary types (e.g. .pdf, .docx, images), returns guidance — use Bash or a workspace skill instead."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Path to file"},
            "offset": {"type": "integer", "description": "Start line (1-indexed)", "default": 1},
            "limit": {
                "type": "integer",
                "description": "Max lines",
                "default": settings.tool_read_default_limit,
            },
        },
        "required": ["file_path"],
    },
    handler=_read,
    categories=["file"],
)


def _write_sync(fpath: str, content: str, file_path: str, *, mode: str = "overwrite") -> str:
    try:
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        if mode.strip().lower() == "append" and os.path.exists(fpath):
            with open(fpath, "a", encoding="utf-8") as f:
                f.write(content)
        else:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)
        from koraku.channels.file_attachments import record_host_file_if_imessage

        record_host_file_if_imessage(fpath, logical_path=file_path)
        action = "Appended" if mode.strip().lower() == "append" else "Wrote"
        return f"{action} {len(content)} chars to {file_path}"
    except Exception as e:
        return f"Error: {e}"


async def _write(file_path: str, content: str, mode: str = "overwrite") -> str:
    """Write content to a file."""
    from koraku.tools.blaxel_dispatch import blaxel_write_if_active

    bx = await blaxel_write_if_active(file_path, content, mode=mode)
    if bx is not None:
        return bx
    host_block = await _host_file_tool_block()
    if host_block:
        return host_block

    fpath, path_error = _resolve_host_path(file_path, parent_for_new_file=True)
    if path_error:
        return path_error
    assert fpath is not None
    return await asyncio.to_thread(_write_sync, fpath, content, file_path, mode=mode)


write_tool = Tool(
    name="Write",
    description=(
        "Write content to a file. Creates parent dirs if needed. "
        "Use workspace-relative paths only (e.g. outputs/presentations/deck.pptx) — "
        "never absolute host paths like /Users/.../koraku-cloud. "
        "For very large files, use mode=append in ~32KB chunks across multiple calls."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Path to file"},
            "content": {"type": "string", "description": "Content to write"},
            "mode": {
                "type": "string",
                "enum": ["overwrite", "append"],
                "description": "overwrite (default) or append to existing file",
                "default": "overwrite",
            },
        },
        "required": ["file_path", "content"],
    },
    handler=_write,
    categories=["file"],
)


def _edit_sync(fpath: str, old_string: str, new_string: str, file_path: str) -> str:
    if not os.path.exists(fpath):
        return f"Error: File not found: {file_path}"
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        if old_string not in content:
            return "Error: old_string not found in file."
        content = content.replace(old_string, new_string, 1)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)
        from koraku.channels.file_attachments import record_host_file_if_imessage

        record_host_file_if_imessage(fpath, logical_path=file_path)
        return f"Edited {file_path}"
    except Exception as e:
        return f"Error: {e}"


async def _edit(file_path: str, old_string: str, new_string: str) -> str:
    """Edit a file by replacing old_string with new_string."""
    from koraku.tools.blaxel_dispatch import blaxel_edit_if_active

    bx = await blaxel_edit_if_active(file_path, old_string, new_string)
    if bx is not None:
        return bx
    host_block = await _host_file_tool_block()
    if host_block:
        return host_block

    fpath, path_error = _resolve_host_path(file_path)
    if path_error:
        return path_error
    assert fpath is not None
    return await asyncio.to_thread(_edit_sync, fpath, old_string, new_string, file_path)


edit_tool = Tool(
    name="Edit",
    description="Replace old_string with new_string in a file. First occurrence only.",
    input_schema={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Path to file"},
            "old_string": {"type": "string", "description": "Exact text to replace"},
            "new_string": {"type": "string", "description": "Replacement text"},
        },
        "required": ["file_path", "old_string", "new_string"],
    },
    handler=_edit,
    categories=["file"],
)


async def _bash(command: str, timeout: int = 30) -> str:
    """Execute a shell command."""
    from koraku.tools.blaxel_dispatch import blaxel_bash_if_active

    bx = await blaxel_bash_if_active(command, timeout)
    if bx is not None:
        return bx
    host_block = await _host_file_tool_block()
    if host_block:
        return host_block

    dangerous = ["rm -rf /", "> /dev/sda", "mkfs", "dd if=/dev/zero"]
    for d in dangerous:
        if d in command:
            return f"Error: Blocked dangerous command: {command}"
    env = os.environ.copy()
    env["KORAKU_PYTHON"] = sys.executable
    proc = await asyncio.create_subprocess_shell(
        command,
        cwd=_effective_workspace_root(),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return f"Error: Timeout after {timeout}s"
    output = stdout.decode("utf-8", errors="replace")
    if stderr:
        output += "\n[stderr]\n" + stderr.decode("utf-8", errors="replace")
    cap = int(settings.tool_bash_output_max_chars)
    if len(output) > cap:
        return output[:cap] + f"\n...[truncated: bash output exceeded {cap} chars]"
    return output


bash_tool = Tool(
    name="Bash",
    description=(
        "Run a shell command. Use for git, scripts, pip installs, and heredoc file creation. "
        "In the Blaxel sandbox, `.koraku-venv` is auto-created on first use — run Python as "
        "`python script.py` after installing packages with pip."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command"},
            "timeout": {"type": "integer", "description": "Timeout seconds", "default": 30},
        },
        "required": ["command"],
    },
    handler=_bash,
    categories=["file", "system"],
)


def _glob_sync(search_dir: str, pattern: str) -> str:
    if not os.path.isdir(search_dir):
        return f"Error: Dir not found: {search_dir}"
    matches = pyglob.glob(os.path.join(search_dir, "**", pattern), recursive=True)
    results = [os.path.relpath(m, search_dir) for m in matches[:30]]
    return json.dumps(results, indent=2)


async def _glob(pattern: str, path: str = ".") -> str:
    """Find files matching a glob pattern."""
    from koraku.tools.blaxel_dispatch import blaxel_glob_if_active

    bx = await blaxel_glob_if_active(pattern, path)
    if bx is not None:
        return bx
    host_block = await _host_file_tool_block()
    if host_block:
        return host_block

    search_dir, path_error = _resolve_host_path(path)
    if path_error:
        return path_error
    assert search_dir is not None
    return await asyncio.to_thread(_glob_sync, search_dir, pattern)


glob_tool = Tool(
    name="Glob",
    description="Find files matching a pattern like '*.py' or 'src/**/*.ts'.",
    input_schema={
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Glob pattern"},
            "path": {"type": "string", "description": "Base directory", "default": "."},
        },
        "required": ["pattern"],
    },
    handler=_glob,
    categories=["file"],
)


def _grep_sync(search_dir: str, pattern: str, include: str, *, single_file: str | None = None) -> str:
    match_cap = int(settings.tool_grep_max_matches)
    if single_file:
        fpath = single_file
        if not os.path.isfile(fpath):
            return f"Error: File not found: {fpath}"
        regex = re.compile(pattern)
        results: list[str] = []
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f, 1):
                    if regex.search(line):
                        rel = os.path.relpath(fpath, os.path.dirname(fpath) or ".")
                        results.append(f"{rel}:{i}: {line.rstrip()}")
                        if len(results) >= match_cap:
                            break
        except OSError as e:
            return f"Error: {e}"
        return "\n".join(results) if results else "No matches."
    if not os.path.isdir(search_dir):
        return f"Error: Dir not found: {search_dir}"
    results = []
    regex = re.compile(pattern)
    count = 0
    for root, _, files in os.walk(search_dir):
        for fname in files:
            if not pyglob.fnmatch.fnmatch(fname, include):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if regex.search(line):
                            rel = os.path.relpath(fpath, search_dir)
                            results.append(f"{rel}:{i}: {line.rstrip()}")
                            count += 1
                            if count >= match_cap:
                                break
            except OSError:
                continue
        if count >= match_cap:
            break
    if not results:
        return "No matches."
    return "\n".join(results[:match_cap])


async def _grep(pattern: str, path: str = ".", include: str = "*") -> str:
    """Search file contents with regex."""
    from koraku.tools.blaxel_dispatch import blaxel_grep_if_active

    bx = await blaxel_grep_if_active(pattern, path, include)
    if bx is not None:
        return bx
    host_block = await _host_file_tool_block()
    if host_block:
        return host_block

    resolved, path_error = _resolve_host_path(path)
    if path_error:
        return path_error
    assert resolved is not None
    raw = (path or "").strip()
    if raw and not raw.endswith("/") and os.path.isfile(resolved):
        return await asyncio.to_thread(_grep_sync, resolved, pattern, include, single_file=resolved)
    if not os.path.isdir(resolved):
        return f"Error: Dir not found: {path}"
    return await asyncio.to_thread(_grep_sync, resolved, pattern, include)


grep_tool = Tool(
    name="Grep",
    description=(
        "Search file contents with regex. Returns file:line matches. "
        "path is usually a directory; a file path also works (searches that file only)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern"},
            "path": {"type": "string", "description": "Directory or file path", "default": "."},
            "include": {"type": "string", "description": "File filter like '*.py'", "default": "*"},
        },
        "required": ["pattern"],
    },
    handler=_grep,
    categories=["file"],
)


async def _todo_write(merge: bool = True, todos: list | None = None) -> str:
    """Merge or replace the session todo list (in-memory for this chat request)."""
    from koraku.tools.runtime import get_active_session

    session = get_active_session()
    if session is None:
        return "Error: TodoWrite is only available during an agent run."

    incoming = todos or []
    if not isinstance(incoming, list):
        return "Error: todos must be a list of objects with id, content, and status."

    if not merge:
        session.todos = [t for t in incoming if isinstance(t, dict) and t.get("id")]
    else:
        by_id: dict[str, dict[str, Any]] = {}
        for t in session.todos:
            if isinstance(t, dict) and t.get("id") is not None:
                by_id[str(t["id"])] = dict(t)
        for t in incoming:
            if isinstance(t, dict) and t.get("id") is not None:
                tid = str(t["id"])
                by_id[tid] = {**by_id.get(tid, {}), **t}
        session.todos = list(by_id.values())

    session.touch()
    return json.dumps({"todos": session.todos}, indent=2, ensure_ascii=False)


todo_write_tool = Tool(
    name="TodoWrite",
    description=(
        "Track multi-step work. Pass merge=true to upsert items by id; merge=false replaces the whole list. "
        "Each todo: {id, content, status} where status is pending|in_progress|completed."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "merge": {"type": "boolean", "description": "If true, merge with existing todos by id", "default": True},
            "todos": {
                "type": "array",
                "description": "Todo items",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "content": {"type": "string"},
                        "status": {"type": "string"},
                    },
                    "required": ["id", "content", "status"],
                },
            },
        },
        "required": ["todos"],
    },
    handler=_todo_write,
    categories=["planning"],
)


# ========================================================================
# WEB TOOLS (abstracted — LLM sees generic names)
# ========================================================================

_JINA_READER_BASE = "https://r.jina.ai/"
_JINA_FETCH_TIMEOUT_SECONDS = 30.0
_EXA_FETCH_TIMEOUT_SECONDS = 25.0
_FIRECRAWL_FETCH_TIMEOUT_SECONDS = 45.0


def _jina_reader_url(page_url: str) -> str:
    return f"{_JINA_READER_BASE}{page_url}"


def _web_fetch_max_chars(max_chars: int | None) -> int:
    return int(max_chars if max_chars is not None else settings.tool_web_fetch_max_chars)


async def _web_search(
    query: str,
    num_results: int = 5,
    published_after: str | None = None,
    published_before: str | None = None,
    prefer_recency_days: int | None = None,
) -> str:
    """Search the web using Exa (semantic search with optional published-date window)."""
    if not settings.exa_api_key:
        return "Error: Web search is not available (Exa API key not configured)."

    url = "https://api.exa.ai/search"
    headers = {"Authorization": f"Bearer {settings.exa_api_key}", "Content-Type": "application/json"}
    payload: dict[str, Any] = {
        "query": query,
        "numResults": min(num_results, 10),
        "useAutoprompt": True,
        # Hybrid routing — often better for SKUs, retailers, and exact product names than pure neural.
        "type": "auto",
    }
    pa = (published_after or "").strip()
    pb = (published_before or "").strip()
    if pa:
        payload["startPublishedDate"] = pa
    if pb:
        payload["endPublishedDate"] = pb
    if not pa and not pb and prefer_recency_days is not None and prefer_recency_days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=int(prefer_recency_days))
        payload["startPublishedDate"] = cutoff.strftime("%Y-%m-%dT00:00:00.000Z")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
        except Exception as e:
            return f"Error: Search failed: {e}"

    data = resp.json()
    if isinstance(data, dict) and data.get("error"):
        return f"Error: Search API returned: {data.get('error')}"

    results = []
    for r in data.get("results", []) if isinstance(data, dict) else []:
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("text", "")[:300],
            "score": r.get("score", 0),
        })

    if not results:
        return "Error: Web search returned no results for this query."

    return json.dumps(results, indent=2, ensure_ascii=False)


web_search_tool = Tool(
    name="WebSearch",
    description=(
        "Search the web (Exa). Returns title, URL, snippet per hit. "
        "For prices, availability, or 'current' facts, set prefer_recency_days (e.g. 540) or published_after ISO date."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query; add year/region/SKU when facts are time- or locale-sensitive"},
            "num_results": {"type": "integer", "description": "Number of results (1-10)", "default": 5},
            "published_after": {
                "type": "string",
                "description": "Optional ISO 8601 date; only pages published after this date",
            },
            "published_before": {
                "type": "string",
                "description": "Optional ISO 8601 date; only pages published before this date",
            },
            "prefer_recency_days": {
                "type": "integer",
                "description": "If set (e.g. 365–700), only newer pages — use for prices and news",
            },
        },
        "required": ["query"],
    },
    handler=_web_search,
    categories=["web"],
)


async def _jina_fetch_page(
    url: str,
    *,
    max_chars: int | None = None,
    extract_prompt: str | None = None,
) -> tuple[bool, str]:
    """Fetch page markdown via Jina Reader. Returns (ok, body_or_error_detail)."""
    _ = extract_prompt  # Jina returns full-page markdown; structured extract uses Exa/Firecrawl.
    max_chars = _web_fetch_max_chars(max_chars)
    page_url = (url or "").strip()
    if not page_url:
        return False, "empty URL"

    headers = {"Accept": "text/markdown, text/plain, */*"}
    async with httpx.AsyncClient(timeout=_JINA_FETCH_TIMEOUT_SECONDS, follow_redirects=True) as client:
        try:
            resp = await client.get(_jina_reader_url(page_url), headers=headers)
            resp.raise_for_status()
        except Exception as e:
            return False, f"Jina request failed: {e}"

    text = (resp.text or "").strip()
    if not text:
        return False, "Jina returned no readable text for this URL"

    parts = [f"URL: {page_url}", "(source: Jina Reader)", f"\n--- Content ---\n{text[:max_chars]}"]
    return True, "\n".join(parts)


async def _exa_fetch_page(
    url: str,
    *,
    max_chars: int | None = None,
    extract_prompt: str | None = None,
) -> tuple[bool, str]:
    """Fetch page text via Exa Contents. Returns (ok, body_or_error_detail)."""
    max_chars = _web_fetch_max_chars(max_chars)
    if not settings.exa_api_key:
        return False, "Exa API key not configured"

    page_url = (url or "").strip()
    if not page_url:
        return False, "empty URL"

    headers = {
        "Authorization": f"Bearer {settings.exa_api_key}",
        "Content-Type": "application/json",
    }
    ep = (extract_prompt or "").strip()
    payload: dict[str, Any] = {"urls": [page_url]}
    if ep:
        payload["highlights"] = {"query": ep, "maxCharacters": max_chars}
    else:
        payload["text"] = {"maxCharacters": max_chars}

    async with httpx.AsyncClient(timeout=_EXA_FETCH_TIMEOUT_SECONDS) as client:
        try:
            resp = await client.post("https://api.exa.ai/contents", headers=headers, json=payload)
            resp.raise_for_status()
        except Exception as e:
            return False, f"Exa request failed: {e}"

    data = resp.json()
    if not isinstance(data, dict):
        return False, "Exa returned invalid JSON"

    if data.get("error"):
        return False, f"Exa API error: {data.get('error')}"

    results = data.get("results")
    if not isinstance(results, list) or not results:
        return False, "Exa returned no results for this URL"

    row = results[0] if isinstance(results[0], dict) else {}
    status = str(row.get("status") or "success").lower()
    if status == "error":
        err = row.get("error")
        if isinstance(err, dict):
            detail = str(err.get("message") or err.get("tag") or "unknown error")
        else:
            detail = str(err or "unknown error")
        return False, f"Exa could not read page: {detail}"

    text = (row.get("text") or "").strip()
    if not text:
        highlights = row.get("highlights")
        if isinstance(highlights, list):
            text = "\n".join(str(h).strip() for h in highlights if str(h).strip())
        elif isinstance(highlights, str):
            text = highlights.strip()

    if not text:
        return False, "Exa returned no readable text for this URL"

    title = str(row.get("title") or "").strip()
    parts = [f"URL: {page_url}", "(source: Exa Contents)"]
    if title:
        parts.append(f"Title: {title}")
    parts.append(f"\n--- Content ---\n{text[:max_chars]}")
    return True, "\n".join(parts)


async def _firecrawl_fetch_page(
    url: str,
    only_main_content: bool = True,
    include_html: bool = False,
    extract_prompt: str | None = None,
) -> str:
    """Fetch and scrape a web page using Firecrawl."""
    if not settings.firecrawl_api_key:
        return "Error: Firecrawl API key not configured."

    page_url = (url or "").strip()
    if not page_url:
        return "Error: URL is required."

    # v2 scrape: LLM extraction uses formats[{type:json,prompt}], not v1 top-level "extract".
    api_url = "https://api.firecrawl.dev/v2/scrape"
    headers = {"Authorization": f"Bearer {settings.firecrawl_api_key}", "Content-Type": "application/json"}

    formats: list[Any] = ["markdown"]
    if include_html:
        formats.append("html")
    ep = (extract_prompt or "").strip()
    if ep:
        formats.append({"type": "json", "prompt": ep})

    payload: dict[str, Any] = {
        "url": page_url,
        "onlyMainContent": only_main_content,
        "formats": formats,
    }

    async with httpx.AsyncClient(timeout=_FIRECRAWL_FETCH_TIMEOUT_SECONDS) as client:
        try:
            resp = await client.post(api_url, headers=headers, json=payload)
            resp.raise_for_status()
        except Exception as e:
            return f"Error: Failed to fetch page: {e}"

    data = resp.json()
    if not data.get("success"):
        return f"Error: Fetch failed: {data.get('error', 'Unknown error')}"

    result = data.get("data", {})
    parts = [f"URL: {page_url}", "(source: Firecrawl)"]

    extracted = result.get("json") or result.get("extract")
    if extracted:
        parts.append(f"\n--- Extracted Data ---\n{json.dumps(extracted, indent=2)[:3000]}")

    md = (result.get("markdown") or "").strip()
    if "markdown" in result:
        md_cap = int(settings.tool_web_fetch_max_chars)
        parts.append(f"\n--- Content ---\n{result['markdown'][:md_cap]}")
    
    if "html" in result:
        html_content = result["html"]
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Extract image URLs
        images = []
        for img in soup.find_all("img"):
            src = img.get("src", "")
            alt = img.get("alt", "")
            if src:
                if src.startswith("/"):
                    src = urljoin(page_url, src)
                images.append({"url": src, "alt": alt})
        
        if images:
            parts.append(f"\n--- Images ({len(images)}) ---")
            for img in images[:30]:
                parts.append(f"  {img['url']}" + (f"  [alt: {img['alt']}]" if img["alt"] else ""))
        
        # Extract links
        links = []
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            text = a.get_text(strip=True)
            if href and not href.startswith(("#", "javascript:", "mailto:")):
                links.append({"url": href, "text": text})
        
        if links:
            parts.append(f"\n--- Links ({len(links)}) ---")
            for link in links[:20]:
                parts.append(f"  {link['url']}" + (f"  ({link['text'][:50]})" if link["text"] else ""))

    body = "\n".join(parts)
    if not extracted and not md and "html" not in result:
        return (
            "Error: Page fetch succeeded but returned no readable text. "
            "Try another URL, set include_html=true, or search for a mirror listing."
        )

    return body


async def _web_page(
    url: str,
    only_main_content: bool = True,
    include_html: bool = False,
    extract_prompt: str | None = None,
) -> str:
    """Fetch a URL: Jina Reader first, Exa Contents second, Firecrawl for hard pages / raw HTML."""
    page_url = (url or "").strip()
    if not page_url:
        return "Error: URL is required."

    if include_html and not settings.firecrawl_api_key:
        return "Error: Web page fetching requires FIRECRAWL_API_KEY when include_html=true."

    jina_note = ""
    exa_note = ""
    if not include_html:
        ok, jina_body = await _jina_fetch_page(
            page_url,
            extract_prompt=extract_prompt,
        )
        if ok:
            return jina_body
        jina_note = jina_body

        if settings.exa_api_key:
            ok, exa_body = await _exa_fetch_page(
                page_url,
                extract_prompt=extract_prompt,
            )
            if ok:
                return exa_body
            exa_note = exa_body

    if not settings.firecrawl_api_key:
        notes = [n for n in (jina_note, exa_note) if n]
        if notes:
            return f"Error: {'; '.join(notes)}"
        return "Error: Web page fetching requires FIRECRAWL_API_KEY for this request."

    fc_body = await _firecrawl_fetch_page(
        page_url,
        only_main_content=only_main_content,
        include_html=include_html,
        extract_prompt=extract_prompt,
    )
    attempt_notes = " / ".join(
        note
        for note in (
            f"Jina: {jina_note}" if jina_note else "",
            f"Exa: {exa_note}" if exa_note else "",
        )
        if note
    )
    if tool_stdout_indicates_error(fc_body, tool_name="WebFetch"):
        if attempt_notes:
            return f"{fc_body}\n({attempt_notes})"
        return fc_body

    if attempt_notes:
        return f"{fc_body.rstrip()}\n(Firecrawl fallback — {attempt_notes})"
    return fc_body


web_fetch_tool = Tool(
    name="WebFetch",
    description=(
        "Fetch and read a web page (Jina Reader first, Exa second, Firecrawl fallback). "
        "Use after WebSearch when you need full article text. "
        "Set include_html=true only when you need image URLs from raw HTML."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch"},
            "only_main_content": {"type": "boolean", "description": "Skip nav/ads (default: true)", "default": True},
            "include_html": {"type": "boolean", "description": "Include raw HTML to extract image URLs (default: false)", "default": False},
            "extract_prompt": {"type": "string", "description": "Optional: what specific data to extract, e.g. 'extract all chapter titles and image links'"},
        },
        "required": ["url"],
    },
    handler=_web_page,
    categories=["web"],
)


def web_fetch_available() -> bool:
    # Jina Reader works without API keys; Exa/Firecrawl are optional fallbacks.
    return True

# ========================================================================
# TOOL REGISTRY + ROUTER
# ========================================================================

_BASE_TOOLS: list[Tool] = [
    read_tool, write_tool, edit_tool, bash_tool, glob_tool, grep_tool, todo_write_tool,
    web_search_tool, web_fetch_tool,
]

from koraku.core.product_hooks import extra_agent_tools  # noqa: E402
from koraku.plugins.memory import memory_agent_tools  # noqa: E402

_AVAILABLE_TOOLS_CACHE: list[Tool] | None = None


def _build_available_tools() -> list[Tool]:
    """Assemble tool list (lazy — avoids importing ``koraku_cloud`` during ``koraku`` init)."""
    tools: list[Tool] = list(_BASE_TOOLS)
    tools.extend(memory_agent_tools())
    tools.extend(extra_agent_tools())
    out: list[Tool] = []
    for t in tools:
        if t.name == "WebSearch" and not settings.exa_api_key:
            continue
        if t.name == "WebFetch" and not web_fetch_available():
            continue
        out.append(t)
    return out


def available_tools() -> list[Tool]:
    global _AVAILABLE_TOOLS_CACHE
    if _AVAILABLE_TOOLS_CACHE is None:
        _AVAILABLE_TOOLS_CACHE = _build_available_tools()
    return _AVAILABLE_TOOLS_CACHE


def __getattr__(name: str) -> list[Tool]:
    if name == "AVAILABLE_TOOLS":
        return available_tools()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# Shell and arbitrary process execution are disabled for cloud runs.
_CLOUD_EXCLUDED_TOOL_NAMES: frozenset[str] = frozenset({"Bash"})


def tools_for_execution_target(target: str, *, blaxel_sandbox_active: bool = False) -> list[Tool]:
    """Subset of available tools for the given execution surface.

    Cloud without Blaxel drops Bash (no host shell). Cloud with an active Blaxel sandbox
    exposes Bash again — commands run inside the VM, not on the Koraku API host.
    """
    tools = available_tools()
    if target == "cloud" and not blaxel_sandbox_active:
        return [t for t in tools if t.name not in _CLOUD_EXCLUDED_TOOL_NAMES]
    # ``server`` (in-process backend) and ``local`` (linked desktop; full tools on device).
    return list(tools)


def get_tool(name: str) -> Tool | None:
    from koraku.integrations.composio import get_registered_composio_tool

    ct = get_registered_composio_tool(name)
    if ct is not None:
        return ct
    resolved = "WebFetch" if name == "WebPage" else name
    for t in available_tools():
        if t.name == resolved:
            return t
    return None


def get_tool_schemas() -> list[dict[str, Any]]:
    return [t.to_anthropic_schema() for t in available_tools()]
