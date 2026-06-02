# Koraku data lifecycle

Engineering map of what the backend stores, processes, and depends on. Use for security reviews, support, and export/delete design. **Not** a legal privacy policy.

## High-level flows

| Flow | Primary stores | Third parties |
|------|----------------|---------------|
| Chat (`POST /stream`) | Session store (memory or Redis); optional Supabase chat history; SSE to browser | LLM; optional Exa/Firecrawl; Composio; Blaxel when `execution_target=cloud` |
| Detached runs (`POST /runs`) | In-process or Redis buffer + replay | Same as chat |
| Automations | Supabase `koraku_automation*` (scoped by `org_id`) | LLM; tools as configured |
| Personalization | Supabase `koraku_personalization` **per `(user_id, org_id)`**; optional workspace files | Supabase |
| iMessage | SendBlue webhook → agent; optional voice transcription | SendBlue; Whisper (Fireworks/OpenAI) |

## Components

### Browser ↔ Next.js BFF (`/koraku-api/*`)

- Adds Supabase Bearer + `X-Koraku-Org-Id` from httpOnly cookies before proxying to the Python API.
- Does not log or persist message bodies; streams SSE through without buffering where possible.

### Detached chat runs

- SSE chunks buffered on the API worker (or Redis when `DETACHED_RUN_STORE_BACKEND=auto` and Redis is up) for reconnect via `GET /runs/{id}/stream` with `?after=` or `Last-Event-ID`.
- `GET /runs/{id}/status` → `running` | `completed` | `not_found`.
- Web client may store `{ runId, after, threadId }` in `localStorage` (`useKorakuChat.ts`); not a server audit log.

### Chat sessions

- **What:** Messages, todos, step state (`koraku/agent/sessions.py` + optional Redis).
- **TTL:** `session_ttl_hours`, `session_store_max` (see `/health/detail`).
- **PII:** Full conversation text for active sessions.

### Supabase (when configured)

| Area | Module | Notes |
|------|--------|--------|
| Chat history | `supabase_chat_history.py` | `chat_thread` / `chat_message`, org-scoped |
| Personalization | `supabase_personalization.py` | Composite key `(user_id, org_id)` |
| Automations | `automations/supabase_store.py` | Cron specs + run history, org-scoped |
| Phone link | `supabase_external.py` | iMessage number verification |

`SUPABASE_SERVICE_ROLE_KEY` is server-only. JWT verification: `SUPABASE_JWT_SECRET` or JWKS.

### Composio

OAuth toolkits; tokens held by Composio. Tool results may appear in LLM context and logs.

### Blaxel sandboxes

Ephemeral VM workspace for cloud execution. Lifecycle governed by Blaxel.

### LLM providers

Prompts and tool definitions sent per provider terms; Koraku does not control provider retention.

### Logs

Use `koraku/core/redact.py` before logging user-controlled strings. Prefer `run_id`, `session_id` over raw payloads.

## User data operations (web)

- **Export:** `GET /api/account/export` — threads, messages, personalization rows (all orgs), automations, recent runs.
- **Delete:** `POST /api/account/delete-data` — cascades user-owned Supabase rows; review Composio disconnect separately.

## Operational settings

Live values: `GET /health/detail` with `HEALTH_DETAIL_TOKEN`. Public UI liveness: `GET /health` (minimal fields including `detached_runs_redis`).

Key timeouts (env names mirror `koraku/core/config.py`):

- `agent_llm_stream_timeout_seconds`
- `agent_tool_phase_timeout_seconds`
- `blaxel_sandbox_ready_timeout_seconds`
