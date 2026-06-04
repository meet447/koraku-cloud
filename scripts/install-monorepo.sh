#!/usr/bin/env bash
# Single venv in this repo (``.venv``). Editable SDK + koraku_cloud for local Cloud dev.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
VENV="$ROOT/.venv"

if [[ ! -d "$VENV" ]]; then
  python3 -m venv "$VENV"
fi

"$VENV/bin/pip" install -U pip
"$VENV/bin/pip" install -e ".[dev,all]"
"$VENV/bin/pip" install -e "./koraku_cloud"

echo ""
echo "Installed into: $VENV"
echo "Activate:  source .venv/bin/activate"
echo "Run API:   ./scripts/run-api.sh"
echo ""
echo "Use only this venv for koraku-cloud. Remove stray envs if needed:"
echo "  ./scripts/cleanup-extra-venvs.sh"
