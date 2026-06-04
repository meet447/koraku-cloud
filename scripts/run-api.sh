#!/usr/bin/env bash
# Run the HTTP API with uvicorn (no global console script). Requires ./scripts/install-monorepo.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
VENV="$ROOT/.venv"
UVICORN="$VENV/bin/uvicorn"

if [[ ! -x "$UVICORN" ]]; then
  echo "Missing $UVICORN — run: ./scripts/install-monorepo.sh" >&2
  exit 1
fi

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
APP="${KORAKU_UVICORN_APP:-}"

if [[ -z "$APP" ]]; then
  if [[ "${KORAKU_SERVER_APP:-cloud}" == "sdk" ]]; then
    APP="koraku.server_sdk:app"
  else
    APP="koraku_cloud.app:app"
  fi
fi

RELOAD="${UVICORN_RELOAD:-true}"
WORKERS="${WEB_CONCURRENCY:-${UVICORN_WORKERS:-1}}"

echo "Python: $VENV/bin/python3"
echo "App:    $APP"
echo "Listen: http://$HOST:$PORT"

ARGS=( "$APP" --host "$HOST" --port "$PORT" )
if [[ "$WORKERS" -gt 1 ]]; then
  exec "$UVICORN" "${ARGS[@]}" --workers "$WORKERS"
fi
if [[ "$RELOAD" == "1" || "$RELOAD" == "true" || "$RELOAD" == "yes" ]]; then
  exec "$UVICORN" "${ARGS[@]}" --reload
fi
exec "$UVICORN" "${ARGS[@]}"
