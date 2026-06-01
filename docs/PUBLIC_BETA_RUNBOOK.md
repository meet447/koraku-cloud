# Koraku public beta runbook

This is the minimum operational checklist before inviting public users.

## Deployment shape

- Run the Python API as a long-lived VM/container process. Automations use an in-process scheduler, so a serverless-only Python API will not run scheduled jobs reliably.
- Keep the Python API private behind the Next.js app when possible. If it is public, set `CORS_ALLOWED_ORIGINS` to the production web origin and keep `REQUIRE_AUTH_FOR_CHAT=true`.
- Use one Python worker for small 1 GB instances. For multiple workers, configure sticky routing for `/stream`, `/runs`, and `/runs/*` because active sessions and detached buffers are in memory.

## Required production env

- Backend only: `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET` when using HS256 tokens, provider LLM keys, `COMPOSIO_API_KEY`, optional Blaxel keys.
- Browser-safe only: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- Safety defaults: `REQUIRE_AUTH_FOR_CHAT=true`, tight `CORS_ALLOWED_ORIGINS`, `CHAT_RATE_LIMIT_PER_MINUTE`, `AUTOMATION_RATE_LIMIT_PER_MINUTE`.

## Release checklist

- Run Supabase migrations from `web/supabase/migrations`.
- Verify `/health` reports the expected LLM provider, scheduler state, Supabase config, and sandbox mode.
- Exercise sign-up, onboarding, chat, memory save, connection list, automation create/run, data export, and account deletion request.
- Confirm unauthenticated calls to `POST /stream` and `POST /runs` return `401`.
- Confirm production logs redact secrets and include enough context for support: request path, user id when available, run id, automation id, and provider error category.

## Degraded modes

- LLM provider down: chat should return a clear setup/provider error and support should pause marketing traffic.
- Composio unavailable: chat can continue with static tools, but connected-app actions are unavailable.
- Blaxel unavailable: cloud execution is blocked; users should see the sandbox error instead of host file access.
- Scheduler stopped: existing automations remain stored but scheduled runs will not fire until the Python process recovers.

## Manual recovery

- Stuck detached run: ask the user to start a new chat; buffers are in-process and expire.
- Failed automation: inspect the automation run row, verify required connections, then use Run now after fixing credentials or spec.
- Account/data request: export Supabase chat, personalization, automations, automation runs, and any exposed workspace/brain files; delete those records before removing the auth user.