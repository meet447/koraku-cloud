"""Ensure artifact builds run only inside the Blaxel sandbox."""
from __future__ import annotations

from koraku.agent.blaxel_scope import get_active_blaxel_sandbox


async def require_sandbox_for_artifacts() -> str | None:
    """Return an error message when artifact tools cannot run in the sandbox."""
    from koraku.agent.runtime_context import get_active_execution_target
    from koraku.integrations.blaxel_lazy import cloud_file_tool_block_reason
    from koraku.integrations.blaxel_runtime import cloud_blaxel_block_reason
    from koraku.core.config import settings

    if get_active_execution_target() != "cloud":
        return (
            "Error: Artifact builds are sandbox-only. Switch to Sandbox mode "
            "(execution_target=cloud) — host filesystem is not used for documents or decks."
        )

    config_block = cloud_blaxel_block_reason(settings)
    if config_block:
        return f"Error: {config_block}"

    block = await cloud_file_tool_block_reason(try_ensure=True)
    if block:
        return block

    if get_active_blaxel_sandbox() is None:
        return "Error: Blaxel sandbox is not available for artifact builds."
    return None


async def read_json_spec_from_sandbox(spec_path: str) -> tuple[dict | None, str | None]:
    """Read a JSON spec file from the active Blaxel session workspace."""
    import json
    import shlex

    from koraku.tools.blaxel_dispatch import blaxel_bash_if_active

    rel = (spec_path or "").strip().replace("\\", "/")
    if not rel:
        return None, "Error: spec_path is empty."
    raw = await blaxel_bash_if_active(f"cat {shlex.quote(rel)}", timeout=60)
    if raw is None:
        return None, "Error: Blaxel sandbox is not active."
    if raw.startswith("Error"):
        return None, raw
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        return None, f"Error: spec file is not valid JSON: {e}"
    if not isinstance(parsed, dict):
        return None, "Error: spec file must contain a JSON object."
    return parsed, None
