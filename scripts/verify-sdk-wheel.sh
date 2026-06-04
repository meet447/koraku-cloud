#!/usr/bin/env bash
# Build the public SDK wheel and assert koraku_cloud is not bundled.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 -m pip install -q build
rm -rf dist build *.egg-info koraku.egg-info 2>/dev/null || true
python3 -m build --wheel

WHEEL="$(ls -1 dist/koraku-*.whl | head -1)"
echo "Wheel: $WHEEL"

if unzip -l "$WHEEL" | grep -q 'koraku_cloud/'; then
  echo "FAIL: wheel contains koraku_cloud/" >&2
  unzip -l "$WHEEL" | grep 'koraku_cloud/' >&2
  exit 1
fi

# Shims may remain in koraku/ for compat; cloud implementation must not ship.
if unzip -l "$WHEEL" | grep -qE 'koraku_cloud/integrations/|koraku_cloud/api/'; then
  echo "FAIL: wheel contains koraku_cloud product modules" >&2
  exit 1
fi

echo "OK: SDK wheel has no koraku_cloud package tree."
