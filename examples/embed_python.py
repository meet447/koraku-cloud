#!/usr/bin/env python3
"""Minimal embed example — in-process Koraku agent (no HTTP server)."""
from __future__ import annotations

import asyncio
import os

from koraku import Koraku, KorakuConfig


async def main() -> None:
    config = KorakuConfig(
        llm_provider=os.environ.get("LLM_PROVIDER", "fireworks"),
        fireworks_api_key=os.environ.get("FIREWORKS_API_KEY", ""),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        require_auth_for_chat=False,
        execution_target="server",
    )
    agent = Koraku(config)

    async for event in agent.stream("Say hello in one short sentence."):
        typ = event.get("type")
        if typ == "agent.final":
            data = event.get("data") or {}
            print("FINAL:", data.get("text") or data)
        elif typ in ("agent.error", "agent.warning"):
            print(typ.upper(), event.get("data"))


if __name__ == "__main__":
    asyncio.run(main())
