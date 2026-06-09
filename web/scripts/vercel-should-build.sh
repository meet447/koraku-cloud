#!/usr/bin/env bash
# Vercel Ignored Build Step — runs with Root Directory set to `web/`.
# Exit 0 = skip deployment, 1 = build.
set -euo pipefail

if [[ -z "${VERCEL_GIT_PREVIOUS_SHA:-}" || -z "${VERCEL_GIT_COMMIT_SHA:-}" ]]; then
  exit 1
fi

if git diff --quiet "$VERCEL_GIT_PREVIOUS_SHA" "$VERCEL_GIT_COMMIT_SHA" -- .; then
  exit 0
fi

exit 1
