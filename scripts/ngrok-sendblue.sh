#!/usr/bin/env bash
# Expose local Koraku API (:8000) for SendBlue inbound webhooks.
#
# One-time: https://dashboard.ngrok.com/get-started/your-authtoken
#   ngrok config add-authtoken YOUR_TOKEN
# Or: export NGROK_AUTHTOKEN=... before running this script.
set -euo pipefail

API_PORT="${KORAKU_API_PORT:-8000}"
API_URL="http://127.0.0.1:${API_PORT}"

if ! command -v ngrok >/dev/null 2>&1; then
  echo "ngrok not found. Install: brew install ngrok/ngrok/ngrok"
  exit 1
fi

if [[ -n "${NGROK_AUTHTOKEN:-}" ]]; then
  ngrok config add-authtoken "$NGROK_AUTHTOKEN" >/dev/null 2>&1 || true
fi

if ! curl -sf "${API_URL}/health" >/dev/null; then
  echo "Koraku API is not reachable at ${API_URL}/health"
  echo "Start it first: python main.py   (or koraku-server)"
  exit 1
fi

echo "Starting ngrok → ${API_URL}"
echo "Inspector: http://127.0.0.1:4040"
echo ""
echo "SendBlue webhook URL (set in SendBlue dashboard):"
echo "  https://<ngrok-host>/sendblue/webhook"
echo ""
echo "Press Ctrl+C to stop."
exec ngrok http "$API_PORT"
