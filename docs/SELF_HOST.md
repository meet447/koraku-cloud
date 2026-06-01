# Self-host Koraku (OSS)

Run the full Koraku webapp on your laptop, home server, or VM — no Koraku Cloud account required.

## Quick pick

| You want… | Use |
|-----------|-----|
| Fastest try | [Docker Compose](#docker-compose-recommended) |
| Dev / hacking | [Manual install](#manual-install) |
| Production VM | Compose or manual + [runbook](PUBLIC_BETA_RUNBOOK.md) |
| Embed agent only | [SDK.md](SDK.md) — no `web/` required |

## Docker Compose (recommended)

**Requirements:** Docker Desktop or Docker Engine + Compose v2.

```bash
git clone https://github.com/meet447/koraku.git
cd koraku
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

Without an LLM key, chat shows a configuration message from the agent. For a quick try, add `FIREWORKS_API_KEY` or configure an OpenAI-compatible provider (see `.env.example`).

### With Supabase (sign-in + chat history)

1. Create a Supabase project and run migrations from `web/supabase/migrations/` (`cd web && npm run db:migrate`).
2. Set in `.env` (backend) and pass through Compose:
   - `SUPABASE_JWT_SECRET`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
   - `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`
3. Keep `REQUIRE_AUTH_FOR_CHAT=true`.

### Where tools run (OSS default)

The chat composer offers two **OSS** choices (not Koraku Cloud — see [PRODUCT.md](PRODUCT.md)):

- **This computer** — tools on the machine running the API (your laptop when self-hosting).
- **Sandbox** — isolated Blaxel VM when `BLAXEL_*` is configured.

Without Blaxel, use **This computer** only.

## Manual install

```bash
# Backend
python3 -m venv venv && source venv/bin/activate
pip install -e ".[all]"
cp .env.example .env   # edit LLM keys
python main.py        # :8000

# Web (second terminal) — Node 22 LTS recommended (see `.nvmrc`; avoid Node 23)
cd packages/koraku-client && npm install && npm run build
cd ../web && npm install && cp ../.env.example .env.local
# Do not run `npm audit fix --force` in web/ — it downgrades Next to 9.x and breaks React 19.
npm run dev             # :3000
```

Set `KORAKU_BACKEND_URL=http://127.0.0.1:8000` in `web/.env.local` if needed.

## Environment highlights

| Variable | OSS default | Notes |
|----------|-------------|-------|
| `REQUIRE_AUTH_FOR_CHAT` | `true` | Set `false` for local demo |
| `AUTH_BACKEND` | `supabase` | `api_key` or `none` for embeds |
| `SESSION_STORE_BACKEND` | `memory` | `redis` + Upstash for multi-worker |
| `ALLOW_LOCAL_EXECUTION_IN_CHAT` | `true` | **This computer** — tools on the API host (no Blaxel) |
| `ALLOW_SERVER_EXECUTION_IN_CHAT` | `true` | Same host tools via `execution_target=server` (API alias) |
| `BLAXEL_CLOUD_SANDBOX_ENABLED` | `false` | Set `true` + keys for **Cloud** sandboxes |

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Chat says Blaxel / sandbox error | Use **This computer** instead of **Sandbox**, or configure Blaxel keys |
| `401` on chat | Sign in via Supabase or set `REQUIRE_AUTH_FOR_CHAT=false` for demo |
| Web can't reach API | Check `KORAKU_BACKEND_URL` and `docker compose logs api` |
| Automations don't run | Need Supabase + scheduler; API must stay running (not serverless) |

## What's next

See [ROADMAP.md](ROADMAP.md) for OSS vs Koraku Cloud scope.
