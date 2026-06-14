# Self-host Koraku

Run the full Koraku webapp on your laptop, home server, or VM.

## Quick pick

| You want… | Use |
|-----------|-----|
| Fastest try | [Docker Compose](#docker-compose-recommended) |
| Dev / hacking | [Manual install](#manual-install) |
| Production VM | Compose or manual + [production checklist](#production-checklist) |
| Embed agent only | [SDK.md](SDK.md) — no `web/` required |
| iMessage / SMS | [SENDBLUE.md](SENDBLUE.md) |

## Docker Compose (recommended)

**Requirements:** Docker Desktop or Docker Engine + Compose v2.

```bash
git clone https://github.com/meet447/koraku-cloud.git
cd koraku-cloud
cp .env.example .env
# Add at least one LLM key (Fireworks, Anthropic, or an OpenAI-compatible provider — see .env.example)

docker compose up --build
```

- **Web UI:** http://localhost:3000  
- **API health:** http://localhost:8000/health  

### Demo mode (no LLM API key, no Supabase)

In `.env`:

```bash
REQUIRE_AUTH_FOR_CHAT=false
# Leave NEXT_PUBLIC_SUPABASE_* unset — web opens /app without sign-in
# Add FIREWORKS_API_KEY (or another provider below) for real model responses
```

Without an LLM key, chat shows a configuration message from the agent.

### With Supabase (sign-in + persistence)

1. Create a Supabase project and run migrations from `web/supabase/migrations/` (`cd web && npm run db:migrate`).
2. Set in `.env` (backend) and pass through Compose:
   - `SUPABASE_JWT_SECRET`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
   - `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`
3. Keep `REQUIRE_AUTH_FOR_CHAT=true`.

Org-scoped data (chat, automations, personalization) uses `X-Koraku-Org-Id` from the web app cookie after migrations through `20250602160000`.

### Where tools run

The chat composer offers:

- **This computer** — tools on the machine running the API (your laptop when self-hosting).
- **Sandbox** — isolated Blaxel VM when `BLAXEL_*` is configured.

**Sandbox** is Blaxel isolation, not a Koraku-operated hosted product. Without Blaxel, use **This computer** only.

## Manual install

**Recommended:** use `./scripts/install-monorepo.sh` (creates **only** `koraku-cloud/.venv` with editable SDK + `koraku_cloud`).

```bash
# Backend
./scripts/install-monorepo.sh
source .venv/bin/activate
cp .env.example .env   # edit LLM keys
./scripts/run-api.sh    # :8000 (uvicorn)

# Web (second terminal) — Node 22 LTS recommended (see `.nvmrc`)
cd packages/koraku-client && npm install && npm run build
cd ../web && npm install && cp ../.env.example .env.local
npm run dev             # :3000
```

Equivalent without the script:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[all]"
pip install -e "./koraku_cloud"
```

Set `KORAKU_BACKEND_URL=http://127.0.0.1:8000` in `web/.env.local` if needed.

The Next.js app proxies authenticated API traffic through **`/koraku-api/*` route handlers** (SSE and JSON). Only **`/koraku-api/health`** rewrites directly (public liveness). All other backend calls go through handlers that attach Supabase Bearer from cookies and return **401** when there is no session. See `web/src/lib/koraku-backend-proxy.ts` and `web/src/lib/koraku-api-routes.ts`.

## Environment highlights

| Variable | Default | Notes |
|----------|---------|--------|
| `REQUIRE_AUTH_FOR_CHAT` | `true` | Set `false` for local demo |
| `SESSION_STORE_BACKEND` | `redis` when `REDIS_URL` set | Required for multi-worker |
| `DETACHED_RUN_STORE_BACKEND` | `auto` | Redis-backed detached runs when available |
| `HEALTH_DETAIL_TOKEN` | — | Ops snapshot at `GET /health/detail` |
| `SENDBLUE_WEBHOOK_SECRET` | — | Required when SendBlue is enabled |
| `ALLOW_LOCAL_EXECUTION_IN_CHAT` | `true` | **This computer** |
| `BLAXEL_CLOUD_SANDBOX_ENABLED` | `false` | **Sandbox** with Blaxel keys |

Full list: [`.env.example`](../.env.example).

## Production checklist

Before inviting real users:

### Deployment shape

- **Cloud product:** start with `koraku_cloud.app:app` and `bootstrap_cloud()` (not `KORAKU_SERVER_APP=sdk`). SDK-only mode is for local embed/demo; it disables Supabase product hooks and opens chat when `REQUIRE_AUTH_FOR_CHAT=false`.
- Run the Python API as a long-lived process (automations use an in-process scheduler; serverless-only API will not run cron jobs reliably).
- Prefer keeping the API private behind the Next.js BFF. If the API is public, set `CORS_ALLOWED_ORIGINS` to your web origin only and keep `REQUIRE_AUTH_FOR_CHAT=true`.
- **Single worker** on small VMs (~1 GB RAM). For multiple workers, set `REDIS_URL`, `SESSION_STORE_BACKEND=redis`, and use Redis detached runs (`DETACHED_RUN_STORE_BACKEND=auto`) or sticky routing for `/runs*`.

### Auth and tenancy

- `REQUIRE_AUTH_FOR_CHAT=true` and `AUTH_BACKEND=supabase` on any internet-facing API.
- `SUPABASE_JWT_SECRET` (HS256) or JWKS for asymmetric project JWTs.
- Org-scoped routes require a valid org membership (`X-Koraku-Org-Id` from the web cookie after sign-in).
- `GET /api/chat-models` requires the same auth as chat when `REQUIRE_AUTH_FOR_CHAT=true` (demo mode with auth off is local-only).

### Platform admin

- Operators manage org credits, limits, and suspensions at **`/admin`** (Dashboard, Organizations).
- Grant access via **`PLATFORM_ADMIN_USER_IDS`** (comma-separated Supabase user UUIDs on the Python API) or a row in **`koraku_platform_admin`**.
- Mutations are written to **`koraku_admin_audit_log`**. See README § Platform admin.

### Blaxel and file tools (Cloud)

- For **Sandbox** / cloud execution: `BLAXEL_CLOUD_SANDBOX_ENABLED=true`, `BL_API_KEY`, `BL_WORKSPACE`, and `DEFAULT_EXECUTION_TARGET=cloud`.
- Without Blaxel, cloud runs must not use host `Read`/`Write`/`Bash` on the API machine — file tools are blocked when Blaxel is required but unavailable.

### Composio

- Set `COMPOSIO_API_KEY` only when using Connections / automations with Composio triggers.
- Per-user Composio identity comes from the signed-in JWT (`sub`). For single-tenant embeds, set explicit `COMPOSIO_USER_ID` — do not rely on the shared `koraku-local` fallback when Composio is configured.
- `/api/composio/*` requires a session when `REQUIRE_AUTH_FOR_CHAT=true` or Cloud product hooks are active (static catalog browse without auth is local demo only).

### Webhooks and secrets

- Automation event webhooks: use `X-Koraku-Webhook-Token` or `?token=`; rotate on leak.
- `SENDBLUE_WEBHOOK_SECRET` when SendBlue is enabled (fail-closed if missing).
- `HEALTH_DETAIL_TOKEN` for `GET /health/detail` (never expose in the browser).
- Service role key (`SUPABASE_SERVICE_ROLE_KEY`) is tier-0 — API host compromise equals database access.

### Required production env

- **Backend (secret):** `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET` (HS256), LLM keys, `COMPOSIO_API_KEY` if using connections, optional Blaxel keys, `HEALTH_DETAIL_TOKEN`, `SENDBLUE_WEBHOOK_SECRET` when SendBlue is on.
- **Browser-safe:** `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` only.
- **Safety:** tight `CORS_ALLOWED_ORIGINS`, `CHAT_RATE_LIMIT_PER_MINUTE`, `AUTOMATION_RATE_LIMIT_PER_MINUTE`.

### Release verification

- Run `cd web && npm run db:migrate`.
- Check `GET /health` (UI) and `GET /health/detail` with your token (ops); Cloud should show `runtime: cloud` in detail when product hooks are registered.
- Exercise sign-up, chat, memory save, connections, automation create/run, data export, account deletion.
- Confirm unauthenticated `POST /stream`, `POST /runs`, and `GET /api/chat-models` return `401` (with auth required).
- Confirm logs redact secrets (`koraku/core/redact.py`).

### Degraded modes

| Failure | Behavior |
|---------|----------|
| LLM down | Clear provider error; pause traffic |
| Composio down | Static tools only |
| Blaxel down | Cloud execution blocked |
| Scheduler down | Automations stored but not fired |

### Manual recovery

- **Stuck detached run:** `GET /runs/{id}/status`; buffers expire after `KORAKU_DETACHED_RUN_GC_SECONDS` (default 600).
- **Failed automation:** inspect run row, fix connections, use Run now.
- **Account deletion:** export then delete Supabase rows (chat, personalization per org, automations) before removing the auth user.

See also [DATA_LIFECYCLE.md](DATA_LIFECYCLE.md) and [SECURITY.md](../SECURITY.md).

## SendBlue / iMessage

See **[SENDBLUE.md](SENDBLUE.md)** for credentials, webhooks, and troubleshooting.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Chat says Blaxel / sandbox error | Use **This computer**, or configure Blaxel |
| `401` on chat | Sign in or set `REQUIRE_AUTH_FOR_CHAT=false` for demo |
| Web can't reach API | `KORAKU_BACKEND_URL`, `docker compose logs api` |
| Automations don't run | Supabase + API must stay running |
| API won't start multi-worker | Set `REDIS_URL` (startup check fails without it) |
| SendBlue webhook 401 | Set `SENDBLUE_WEBHOOK_SECRET` to match SendBlue dashboard |
