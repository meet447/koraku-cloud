# Koraku data lifecycle (Phase B — privacy & trust)

This document is the **engineering data map** for what the backend stores, processes, and depends on. Use it for security reviews, support answers, and retention/export design. It is **not** a legal privacy policy; pair it with your public policy and jurisdiction-specific requirements.

## High-level flows

| Flow | Primary stores | Third parties |
|------|----------------|---------------|
| Chat (`POST /stream`) | In-memory session; optional Supabase chat history; SSE to browser | LLM provider; optional Exa/Firecrawl; Composio when linked; Blaxel VM when cloud execution is on |
| Detached runs (`POST /runs`) | Same as chat, plus in-process replay buffer until GC | Same |
| Automations | Supabase `koraku_*` tables; scheduler triggers headless agent | LLM; tools as configured |
| Personalization / memory snippets | Files under workspace and/or Supabase-backed fields when JWT present | Supabase |

## Per-component notes

### Detached chat runs (`POST /runs`, `GET /runs/{id}/stream`, `GET /runs/{id}/status`)

- **What:** SSE chunks are buffered in RAM on the **API worker** that accepted `POST /runs` so the browser can disconnect and subscribe again with `?after=` or `Last-Event-ID`.
- **Status:** `GET /runs/{id}/status` returns `running` | `completed` | `not_found` (and `last_event_id`) for reconnect UX. `not_found` is normal after in-process GC or if another worker handled the original run.
- **Client:** The web app can persist `{ runId, after, threadId, assistantMsgId }` in `localStorage` to resume after refresh (see `useKorakuChat.ts`). This is **not** a durable server-side audit log.

### In-memory chat sessions (`koraku/agent/sessions.py` + optional Redis via `SESSION_STORE_BACKEND`)

- **What:** Message list, todos, step counters for active browser sessions.
- **TTL / cap:** `session_ttl_hours`, `session_store_max` in settings (see `/health`).
- **Deletion:** Idle expiry and cap eviction; process restart clears all.
- **PII:** Full user/assistant text may reside here for active sessions.

### Supabase (when configured)

- **Chat history** (`koraku/integrations/supabase_chat_history.py`): persisted messages for hydration across devices; content is application-defined JSON/text.
- **Personalization** (`koraku/integrations/supabase_personalization.py`): optional display name, memory, “soul” text fields tied to auth subject.
- **Automations** (`koraku/automations/` + `supabase_store.py`): cron specs, run history, user linkage via service role on the **server only**.
- **Keys:** `SUPABASE_SERVICE_ROLE_KEY` must never ship to the browser; JWT verification uses `SUPABASE_JWT_SECRET` (or asymmetric JWKS as implemented).

### Composio

- **What:** OAuth-linked toolkits (e.g. Gmail, Calendar) exposed as dynamic tools for the signed-in user.
- **Tokens:** Held by Composio / connector per their model; Koraku does not store long-lived provider passwords in the agent repo, but tool **results** may flow through LLM context and logs—treat tool payloads as sensitive.
- **Degraded mode:** If Composio tool load fails, the agent continues with static tools and emits a warning (see `koraku/agent/run.py`).

### Blaxel cloud sandboxes

- **What:** Ephemeral VM workspace per chat session for file/shell tools when cloud execution is enabled.
- **Data:** User files created during the session live in the sandbox path documented to the model; lifecycle is governed by Blaxel and your workspace settings—not Koraku’s Postgres.
- **Operational:** See `cloud_chat_sandbox_block_reason` on `/health` when cloud chat cannot start.

### LLM providers

- **What:** Prompts (system + messages + tool definitions), images inline as configured.
- **Retention:** Governed entirely by the provider’s terms; Koraku does not control provider-side logs.

### Application logs

- **What:** Standard Python logging (e.g. timeouts, detached worker failures, Composio skips).
- **Hygiene:** Use `koraku/core/redact.py` before logging user-controlled strings or exceptions that may echo tokens. Prefer structured fields (`run_id`, `session_id`) over raw payloads.

## Suggested user-facing promises (product work)

1. **Export:** Define what “export my data” includes (Supabase tables + any file workspace paths you expose).
2. **Delete:** Account deletion should cascade chat rows, personalization, automations, and invalidate Composio connections per your integration design.
3. **Retention defaults:** Document default chat retention and how to shorten it for regulated customers.

## Configuration knobs related to reliability (Phase A)

See `/health` for live values:

- `agent_llm_stream_timeout_seconds` — wall-clock cap for one LLM streaming step in interactive chat.
- `agent_tool_phase_timeout_seconds` — wall-clock cap for executing one batch of tool calls in a step.
- `blaxel_sandbox_ready_timeout_seconds` — provisioning wait for cloud sandboxes.

Environment variable names match the settings field names in uppercase with underscores (see `koraku/core/config.py`).
