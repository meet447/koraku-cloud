#!/usr/bin/env python3
"""Apply OSS-only edits after scripts/export-sdk-oss-repo.sh rsync."""
from __future__ import annotations

import re
import sys
from pathlib import Path


def _strip_composio_trigger_types(dest: Path) -> None:
    path = dest / "koraku/api/composio_routes.py"
    text = path.read_text(encoding="utf-8")
    pattern = (
        r"\n\n@router\.get\(\"/trigger-types\".*?"
        r"return \{\"items\": items, \"configured\": True\}\n"
    )
    updated, n = re.subn(pattern, "\n", text, count=1, flags=re.DOTALL)
    if n != 1:
        raise SystemExit(f"expected to remove one trigger-types route from {path}")
    path.write_text(updated, encoding="utf-8")


def _patch_pyproject_urls(dest: Path) -> None:
    path = dest / "pyproject.toml"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "https://github.com/meet447/koraku-cloud",
        "https://github.com/meet447/Koraku",
    )
    if "Documentation =" not in text:
        text = text.replace(
            'Repository = "https://github.com/meet447/Koraku"\n',
            'Repository = "https://github.com/meet447/Koraku"\n'
            'Documentation = "https://github.com/meet447/Koraku/blob/main/docs/SDK.md"\n',
        )
    if "koraku-cloud" not in text.lower() and "# Koraku Cloud" not in text:
        text = text.rstrip() + (
            "\n\n# Koraku Cloud product code lives in "
            "https://github.com/meet447/koraku-cloud (private monorepo).\n"
        )
    path.write_text(text, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} /path/to/Koraku-clone")
    dest = Path(sys.argv[1]).resolve()
    _strip_composio_trigger_types(dest)
    _patch_pyproject_urls(dest)
    print(f"OSS post-export patches applied under {dest}")


if __name__ == "__main__":
    main()
