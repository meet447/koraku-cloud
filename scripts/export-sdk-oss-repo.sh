#!/usr/bin/env bash
# Sync koraku SDK sources into an open-source Koraku git checkout (meet447/Koraku).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${1:-}"

if [[ -z "$DEST" || ! -d "$DEST/.git" ]]; then
  echo "Usage: $0 /path/to/Koraku-clone" >&2
  exit 1
fi

echo "Exporting SDK from $ROOT -> $DEST"

find "$DEST" -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +

mkdir -p "$DEST/scripts" "$DEST/docs" "$DEST/tests" "$DEST/.github/workflows"

rsync -a "$ROOT/koraku/" "$DEST/koraku/"
rsync -a "$ROOT/packages/" "$DEST/packages/"
rsync -a "$ROOT/examples/" "$DEST/examples/"
rsync -a "$ROOT/tests/" "$DEST/tests/"
rsync -a "$ROOT/LICENSE" "$DEST/LICENSE"
rsync -a "$ROOT/pyproject.toml" "$DEST/pyproject.toml"
rsync -a "$ROOT/requirements.txt" "$DEST/requirements.txt" 2>/dev/null || true
rsync -a "$ROOT/scripts/verify-sdk-wheel.sh" "$DEST/scripts/verify-sdk-wheel.sh"
rsync -a "$ROOT/docs/SDK.md" "$DEST/docs/SDK.md"
rsync -a "$ROOT/tests/conftest.py" "$DEST/tests/conftest.py"
rsync -a "$ROOT/CODE_OF_CONDUCT.md" "$DEST/CODE_OF_CONDUCT.md" 2>/dev/null || true
rsync -a "$ROOT/SECURITY.md" "$DEST/SECURITY.md" 2>/dev/null || true
# Drop Cloud-only tests and product automations.
rm -rf "$DEST/tests/automations"
rm -f \
  "$DEST/tests/test_detached_runs.py" \
  "$DEST/tests/test_sdk_no_eager_cloud_import.py" \
  "$DEST/tests/test_supabase_chat_history_trim.py" \
  "$DEST/tests/test_supabase_personalization.py" \
  "$DEST/tests/test_personalization_cache.py" \
  "$DEST/tests/test_server_split.py" \
  "$DEST/tests/test_profiles.py"

chmod +x "$DEST/scripts/verify-sdk-wheel.sh"

# OSS repo metadata and tests that must override the monorepo copies.
rsync -a "$ROOT/scripts/oss-repo/" "$DEST/"

python3 "$ROOT/scripts/oss-repo-post-export.py" "$DEST"

echo "SDK export tree written to $DEST"
