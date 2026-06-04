#!/usr/bin/env bash
# Sync koraku-cloud to the VPS and redeploy Docker Compose (API + Redis).
#
# Quick start:
#   cp deploy/vps/deploy.env.example deploy/vps/deploy.env
#   # edit deploy/vps/deploy.env
#   ./scripts/deploy-vps.sh
#
# Env overrides: KORAKU_VPS_HOST, KORAKU_VPS_USER, KORAKU_VPS_SSH_KEY, KORAKU_VPS_DIR
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DEPLOY_ENV="${KORAKU_VPS_DEPLOY_ENV:-$ROOT/deploy/vps/deploy.env}"
if [[ -f "$DEPLOY_ENV" ]]; then
  # shellcheck disable=SC1090
  source "$DEPLOY_ENV"
fi

VPS_HOST="${KORAKU_VPS_HOST:-}"
VPS_USER="${KORAKU_VPS_USER:-ubuntu}"
VPS_DIR="${KORAKU_VPS_DIR:-/opt/koraku/koraku-cloud}"
SSH_KEY="${KORAKU_VPS_SSH_KEY:-}"
COMPOSE_FILE="${KORAKU_VPS_COMPOSE_FILE:-deploy/vps/docker-compose.yml}"
HEALTH_URL="${KORAKU_VPS_HEALTH_URL:-http://127.0.0.1:8000/health}"
SYNC_ONLY=false
DEPLOY_ONLY=false

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

  Sync the repo to the VPS (rsync) and run:
    docker compose -f $COMPOSE_FILE --env-file .env up -d --build

Options:
  --sync-only     Rsync only; skip Docker redeploy
  --deploy-only   Redeploy on VPS only; skip rsync
  -h, --help      Show this help

Config (first match wins):
  deploy/vps/deploy.env   or  KORAKU_VPS_DEPLOY_ENV
  Environment variables: KORAKU_VPS_HOST, KORAKU_VPS_USER, KORAKU_VPS_SSH_KEY, KORAKU_VPS_DIR

Note: .env on the VPS is never overwritten (server secrets stay on the host).
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --sync-only) SYNC_ONLY=true; shift ;;
    --deploy-only) DEPLOY_ONLY=true; shift ;;
    -h | --help) usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ "$SYNC_ONLY" == true && "$DEPLOY_ONLY" == true ]]; then
  echo "Use only one of --sync-only or --deploy-only." >&2
  exit 1
fi

if [[ -z "$VPS_HOST" ]]; then
  echo "Set KORAKU_VPS_HOST in deploy/vps/deploy.env (see deploy/vps/deploy.env.example)." >&2
  exit 1
fi

SSH=(ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15)
RSYNC_RSH="ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15"
if [[ -n "$SSH_KEY" ]]; then
  if [[ ! -f "$SSH_KEY" ]]; then
    echo "SSH key not found: $SSH_KEY" >&2
    exit 1
  fi
  SSH+=(-i "$SSH_KEY")
  RSYNC_RSH="ssh -i $(printf '%q' "$SSH_KEY") -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15"
fi
SSH+=("${VPS_USER}@${VPS_HOST}")

REMOTE="${VPS_USER}@${VPS_HOST}:${VPS_DIR}/"

echo "Target: ${VPS_USER}@${VPS_HOST}:${VPS_DIR}"

if [[ "$DEPLOY_ONLY" != true ]]; then
  echo "→ Ensuring remote directory exists…"
  "${SSH[@]}" "mkdir -p '$VPS_DIR'"

  echo "→ Rsyncing project (excluding .env, node_modules, .venv)…"
  rsync -az --delete \
    --exclude .git \
    --exclude node_modules \
    --exclude web/node_modules \
    --exclude 'packages/*/node_modules' \
    --exclude .venv \
    --exclude venv \
    --exclude __pycache__ \
    --exclude .pytest_cache \
    --exclude .koraku \
    --exclude .env \
    --exclude .env.local \
    --exclude deploy/vps/deploy.env \
    -e "$RSYNC_RSH" \
    "$ROOT/" "$REMOTE"
fi

if [[ "$SYNC_ONLY" == true ]]; then
  echo "Sync complete (--sync-only)."
  exit 0
fi

echo "→ Building and restarting Docker Compose on VPS…"
"${SSH[@]}" "bash -s" <<REMOTE
set -euo pipefail
cd '$VPS_DIR'
if [[ ! -f .env ]]; then
  echo "Missing .env at $VPS_DIR on the VPS. Copy .env.example and configure secrets first." >&2
  exit 1
fi
docker compose -f '$COMPOSE_FILE' --env-file .env up -d --build
REMOTE

echo "→ Waiting for API health…"
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if "${SSH[@]}" "curl -fsS '$HEALTH_URL' >/dev/null 2>&1"; then
    echo "✓ API healthy at $HEALTH_URL"
    exit 0
  fi
  sleep 3
done

echo "Deploy finished but health check did not pass yet. Check logs:" >&2
echo "  ssh … 'docker compose -f $VPS_DIR/$COMPOSE_FILE logs -f api'" >&2
exit 1
