# Changelog

## Unreleased

### Added
- Org-scoped automations and personalization (`user_id` + `org_id` composite PK)
- Shared BFF proxy (`koraku-backend-proxy`, `koraku-api-routes`) for `/koraku-api/*`
- `GET /health/detail` (token-gated ops snapshot); minimal public `/health`
- SendBlue webhook fail-closed without `SENDBLUE_WEBHOOK_SECRET`; inbound media SSRF allowlist
- Multi-worker Redis startup check; Redis iMessage dedup
- Docker Compose stack for OSS self-host (`docker compose up`)
- Server execution mode for chat without Blaxel (`ALLOW_SERVER_EXECUTION_IN_CHAT`)
- Setup banner when API or LLM is misconfigured
- Local demo: open `/app` without Supabase when auth env vars are unset
- Multi-provider OpenAI-compatible LLM registry (`LLM_OPENAI_COMPAT_IDS`)

### Changed
- Docs: merged production runbook into `SELF_HOST.md`; removed stale `ROADMAP`, `PRODUCT`, `PUBLIC_BETA_RUNBOOK`
- README updated for koraku-cloud repo, BFF architecture, and current health endpoints
- Models settings page reads live provider catalog from the API
- Legacy flat routes redirect via `next.config.ts` instead of stub pages

### Removed
- Deprecated `src/` import shim
- Bonsai demo provider and dummy model toggles
- Redundant `GET /stream` endpoint and duplicate provider-resolution helpers
- `Settings.custom_*` fields (use `CUSTOM_*` env or `LLM_OPENAI_COMPAT_IDS`)
- `sessions` dict shim on `koraku.agent.sessions` and unused `verify_supabase_jwt_bearer` helper

### Changed
- OpenAI-compat provider id `custom_openai` renamed to `custom` (`custom_openai` still accepted in `LLM_OPENAI_COMPAT_IDS`)

## 0.2.0 — 2026-06-01

### Added
- Embeddable `koraku` Python package (`Koraku`, `KorakuConfig`, injectable settings)
- `@koraku/client` TypeScript SSE SDK
- Pluggable auth (`supabase`, `api_key`, `none`) and session store (`memory`, `redis`)
- Release workflow for PyPI + npm (tag `v*`)
- SDK docs (`docs/SDK.md`) and embed example

### Changed
- Python package moved from `src/` to `koraku/`
