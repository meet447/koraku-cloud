"""Industry-standard tool definitions with abstracted web tool names.

Web tools are presented generically to the LLM:
- WebSearch: discovers content (internally uses Exa)
- WebFetch: fetches/scrapes pages (internally uses Firecrawl)

The LLM doesn't need to know about Exa or Firecrawl — it just searches and fetches.
"""
import asyncio
import glob as pyglob
import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from koraku.core.config import settings
from koraku.tools.tool_def import Tool
from koraku.workspace.paths import workspace_dir


# ========================================================================
# CORE FILE TOOLS (always available)
# ========================================================================

def _workspace_realpath() -> str:
    return os.path.realpath(workspace_dir())


def _path_is_under(path: str, root: str) -> bool:
    try:
        return os.path.commonpath([os.path.realpath(path), root]) == root
    except ValueError:
        return False


def _cloud_file_tool_host_blocked() -> str | None:
    """Cloud mode must not read/write the API host filesystem when Blaxel is not active."""
    from koraku.agent.runtime_context import get_active_execution_target

    if get_active_execution_target() != "cloud":
        return None
    if not settings.blaxel_cloud_sandbox_enabled:
        return None
    from koraku.agent.blaxel_scope import get_active_blaxel_sandbox

    if get_active_blaxel_sandbox() is None:
        return (
            "Error: Cloud file tools require the Blaxel sandbox (still starting or unavailable). "
            "Retry shortly."
        )
    return None


def _resolve_host_path(path: str, *, parent_for_new_file: bool = False) -> tuple[str | None, str | None]:
    """Resolve a host file-tool path and enforce the workspace boundary when enabled."""
    fpath = os.path.abspath(os.path.expanduser(path))
    if not settings.host_file_tools_restrict_to_workspace:
        return fpath, None
    root = _workspace_realpath()
    check_path = os.path.dirname(fpath) if parent_for_new_file else fpath
    if not _path_is_under(check_path, root):
        return None, f"Error: Path must stay under workspace: {root}"
    return fpath, None

async def _read(file_path: str, offset: int = 1, limit: int = 100) -> str:
    """Read a file."""
    from koraku.tools.binary_read_paths import format_binary_read_response, should_use_binary_read_branch
    from koraku.tools.blaxel_dispatch import blaxel_read_if_active

    bx = await blaxel_read_if_active(file_path, offset, limit)
    if bx is not None:
        return bx
    host_block = _cloud_file_tool_host_blocked()
    if host_block:
        return host_block

    fpath, path_error = _resolve_host_path(file_path)
    if path_error:
        return path_error
    assert fpath is not None
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
            "limit": {"type": "integer", "description": "Max lines", "default": 100},
        },
        "required": ["file_path"],
    },
    handler=_read,
    categories=["file"],
)


async def _write(file_path: str, content: str) -> str:
    """Write content to a file."""
    from koraku.tools.blaxel_dispatch import blaxel_write_if_active

    bx = await blaxel_write_if_active(file_path, content)
    if bx is not None:
        return bx
    host_block = _cloud_file_tool_host_blocked()
    if host_block:
        return host_block

    fpath, path_error = _resolve_host_path(file_path, parent_for_new_file=True)
    if path_error:
        return path_error
    assert fpath is not None
    try:
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)
        from koraku.channels.file_attachments import record_host_file_if_imessage

        record_host_file_if_imessage(fpath, logical_path=file_path)
        return f"Wrote {len(content)} chars to {file_path}"
    except Exception as e:
        return f"Error: {e}"


write_tool = Tool(
    name="Write",
    description="Write content to a file. Creates parent dirs if needed.",
    input_schema={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Path to file"},
            "content": {"type": "string", "description": "Content to write"},
        },
        "required": ["file_path", "content"],
    },
    handler=_write,
    categories=["file"],
)


async def _edit(file_path: str, old_string: str, new_string: str) -> str:
    """Edit a file by replacing old_string with new_string."""
    from koraku.tools.blaxel_dispatch import blaxel_edit_if_active

    bx = await blaxel_edit_if_active(file_path, old_string, new_string)
    if bx is not None:
        return bx

    fpath, path_error = _resolve_host_path(file_path)
    if path_error:
        return path_error
    assert fpath is not None
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

    dangerous = ["rm -rf /", "> /dev/sda", "mkfs", "dd if=/dev/zero"]
    for d in dangerous:
        if d in command:
            return f"Error: Blocked dangerous command: {command}"
    proc = await asyncio.create_subprocess_shell(
        command,
        cwd=workspace_dir(),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return f"Error: Timeout after {timeout}s"
    output = stdout.decode("utf-8", errors="replace")
    if stderr:
        output += "\n[stderr]\n" + stderr.decode("utf-8", errors="replace")
    return output[:4000]


bash_tool = Tool(
    name="Bash",
    description="Run a shell command. Use for git, file ops, scripts.",
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


async def _glob(pattern: str, path: str = ".") -> str:
    """Find files matching a glob pattern."""
    from koraku.tools.blaxel_dispatch import blaxel_glob_if_active

    bx = await blaxel_glob_if_active(pattern, path)
    if bx is not None:
        return bx

    search_dir, path_error = _resolve_host_path(path)
    if path_error:
        return path_error
    assert search_dir is not None
    if not os.path.isdir(search_dir):
        return f"Error: Dir not found: {search_dir}"
    matches = pyglob.glob(os.path.join(search_dir, "**", pattern), recursive=True)
    results = [os.path.relpath(m, search_dir) for m in matches[:30]]
    return json.dumps(results, indent=2)


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


async def _grep(pattern: str, path: str = ".", include: str = "*") -> str:
    """Search file contents with regex."""
    from koraku.tools.blaxel_dispatch import blaxel_grep_if_active

    bx = await blaxel_grep_if_active(pattern, path, include)
    if bx is not None:
        return bx

    search_dir, path_error = _resolve_host_path(path)
    if path_error:
        return path_error
    assert search_dir is not None
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
                            if count >= 100:
                                break
            except OSError:
                continue
        if count >= 100:
            break
    if not results:
        return "No matches."
    return "\n".join(results[:100])


grep_tool = Tool(
    name="Grep",
    description="Search file contents with regex. Returns file:line matches.",
    input_schema={
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern"},
            "path": {"type": "string", "description": "Directory", "default": "."},
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


async def _web_page(
    url: str,
    only_main_content: bool = True,
    include_html: bool = False,
    extract_prompt: str | None = None,
) -> str:
    """Fetch and scrape a web page using Firecrawl."""
    if not settings.firecrawl_api_key:
        return "Error: Web page fetching is not available (Firecrawl API key not configured)."
    
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
        "url": url,
        "onlyMainContent": only_main_content,
        "formats": formats,
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(api_url, headers=headers, json=payload)
            resp.raise_for_status()
        except Exception as e:
            return f"Error: Failed to fetch page: {e}"

    data = resp.json()
    if not data.get("success"):
        return f"Error: Fetch failed: {data.get('error', 'Unknown error')}"

    result = data.get("data", {})
    parts = [f"URL: {url}"]

    extracted = result.get("json") or result.get("extract")
    if extracted:
        parts.append(f"\n--- Extracted Data ---\n{json.dumps(extracted, indent=2)[:3000]}")

    md = (result.get("markdown") or "").strip()
    if "markdown" in result:
        parts.append(f"\n--- Content ---\n{result['markdown'][:8000]}")
    
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
                    src = urljoin(url, src)
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


web_fetch_tool = Tool(
    name="WebFetch",
    description="Fetch and read any web page. Handles JavaScript-heavy sites. Use to read content, extract data, or find image URLs.",
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

# ========================================================================
# TOOL REGISTRY + ROUTER
# ========================================================================

_BASE_TOOLS: list[Tool] = [
    read_tool, write_tool, edit_tool, bash_tool, glob_tool, grep_tool, todo_write_tool,
    web_search_tool, web_fetch_tool,
]

from koraku.plugins.memory import memory_agent_tools  # noqa: E402
from koraku.profiles import is_cloud_profile  # noqa: E402

_AVAILABLE_TOOLS_CACHE: list[Tool] | None = None


def _build_available_tools() -> list[Tool]:
    """Assemble tool list (lazy — avoids importing ``koraku_cloud`` during ``koraku`` init)."""
    tools: list[Tool] = list(_BASE_TOOLS)
    tools.extend(memory_agent_tools())
    if is_cloud_profile():
        from koraku_cloud.automations.agent_tools import build_automation_tools

        tools.extend(build_automation_tools())
        if settings.sendblue_api_key and settings.sendblue_api_secret and settings.sendblue_from_number:
            from koraku_cloud.tools.imessage_send_tool import IMESSAGE_SEND_TOOL

            tools.append(IMESSAGE_SEND_TOOL)
    out: list[Tool] = []
    for t in tools:
        if t.name == "WebSearch" and not settings.exa_api_key:
            continue
        if t.name == "WebFetch" and not settings.firecrawl_api_key:
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
