#!/usr/bin/env bash
# Remove virtualenvs that are not koraku-cloud/.venv (safe to skip if you use only one env).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

remove_if_present() {
  local path="$1"
  if [[ -d "$path" && "$path" != "$ROOT/.venv" ]]; then
    echo "Removing: $path"
    rm -rf "$path"
  fi
}

remove_if_present "$ROOT/venv"
remove_if_present "$ROOT/../koraku/.venv"
remove_if_present "$ROOT/../koraku/venv"

echo "Keep: $ROOT/.venv"
echo "Run:  ./scripts/install-monorepo.sh && ./scripts/run-api.sh"
