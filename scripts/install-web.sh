#!/usr/bin/env bash
# Install web deps with Node 22 when nvm is available (avoids EBADENGINE on Node 23).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/web"

if command -v nvm >/dev/null 2>&1; then
  # shellcheck source=/dev/null
  export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
  [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
  if nvm install 22.13.1 2>/dev/null; then
    nvm use 22.13.1
  fi
elif [ -f "$ROOT/.nvmrc" ] && command -v fnm >/dev/null 2>&1; then
  (cd "$ROOT" && fnm use)
fi

node -v
npm install "$@"
