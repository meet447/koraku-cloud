"""Single source for the Koraku server process workspace (cwd)."""
from __future__ import annotations

import os


def workspace_dir() -> str:
    """Absolute path to the workspace directory (server cwd)."""
    return os.path.abspath(os.getcwd())
