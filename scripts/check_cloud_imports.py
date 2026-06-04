#!/usr/bin/env python3
"""Fail if koraku/ imports koraku_cloud at module level (except product channels)."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KORAKU = ROOT / "koraku"

ALLOWED_FILES = frozenset({"koraku/channels/imessage_runner.py"})


def _rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _cloud_imports_at_module_level(path: Path) -> list[tuple[int, str]]:
    rel = _rel(path)
    if rel in ALLOWED_FILES:
        return []
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
    hits: list[tuple[int, str]] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "koraku_cloud" or alias.name.startswith("koraku_cloud."):
                    hits.append((node.lineno, f"import {alias.name}"))
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "koraku_cloud" or node.module.startswith("koraku_cloud."):
                hits.append((node.lineno, f"from {node.module} import ..."))
    return hits


def main() -> int:
    violations: list[str] = []
    for path in sorted(KORAKU.rglob("*.py")):
        for lineno, msg in _cloud_imports_at_module_level(path):
            violations.append(f"{_rel(path)}:{lineno}: {msg}")
    if violations:
        print("Disallowed top-level koraku_cloud imports in koraku/:", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        print("Use lazy imports inside functions or move code to koraku_cloud/.", file=sys.stderr)
        return 1
    print("OK: no disallowed top-level koraku_cloud imports in koraku/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
