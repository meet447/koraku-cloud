"""Tool type only (keeps ``integrations`` / ``automations`` imports cycle-free)."""
from __future__ import annotations

import logging
from typing import Any, Callable, Coroutine

log = logging.getLogger(__name__)


class Tool:
    """Represents an agent tool."""

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        handler: Callable[..., Coroutine[Any, Any, str]],
        categories: list[str] | None = None,
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.handler = handler
        self.categories = categories or ["general"]

    def to_anthropic_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }

    def to_compact_prompt(self) -> str:
        """Ultra-compact prompt format for small models."""
        lines = [f"{self.name}: {self.description}"]
        props = self.input_schema.get("properties", {})
        req = self.input_schema.get("required", [])
        params = []
        for pname, pinfo in props.items():
            pdesc = pinfo.get("description", "")
            ptype = pinfo.get("type", "any")
            r = "*" if pname in req else ""
            params.append(f"  {pname}{r} ({ptype}): {pdesc}")
        if params:
            lines.extend(params)
        return "\n".join(lines)

    async def run(self, **kwargs) -> str:
        try:
            result = await self.handler(**kwargs)
            return result
        except Exception as e:
            log.exception("tool %s failed", self.name)
            return f"Error: {e}"
