# SDK / Cloud boundary migration

## Goal

**`koraku`** = embeddable library (PyPI / [Koraku](https://github.com/meet447/Koraku) repo).  
**`koraku_cloud`** = Koraku Cloud SaaS (this repo): Supabase, automations, tenant, product APIs.

Cloud behavior must not be expressed as `if is_cloud_profile()` scattered through `koraku/`. The Cloud app registers **product hooks** at startup; the SDK path is the default when hooks are unset.

## Policy

1. **New product features** → `koraku_cloud/` only.
2. **No new** `is_cloud_profile()` branches in `koraku/` (use hooks or move call sites to Cloud routes).
3. **No top-level** `import koraku_cloud` in `koraku/` (see `scripts/check_cloud_imports.py`).
4. Export SDK to Koraku after each phase; run `verify-sdk-wheel.sh`.

## Phases

| Phase | Status | Work |
|-------|--------|------|
| **1** | Done | Product hooks registry; chat hydration / personalization / post-turn ingest |
| **2** | Done | `koraku_cloud.api.auth_scope` for automations + workspace routes |
| **3** | Done | `cloud_file_tool_block_reason` in `blaxel_lazy`; `_run_blaxel_tool` in `blaxel_dispatch`; host block on all file tools |
| **4** | Done | Runtime via `product_hooks_active()` / `runtime_mode_label()`; tenant, health, tools hooks |
| **5** | Ongoing | Monorepo exports `koraku/` → Koraku repo; Cloud pins released wheel (see below) |

## Phase 1 (hooks)

- `koraku.core.product_hooks` — register / clear optional callables.
- `koraku.api.sdk_session_hydration` — SDK-only session hydration.
- `koraku_cloud.product_hooks` — Supabase hydration, personalization, Supermemory ingest.
- `koraku_cloud.bootstrap.bootstrap_cloud()` — registers hooks after `bind_cloud_settings()`.
- Tests: `conftest` clears hooks with SDK defaults; Cloud tests use `bootstrap_cloud()`.

## Phase 5 — release workflow (until repos fully split)

1. Implement in monorepo `koraku/` → run tests → `./scripts/export-sdk-oss-repo.sh` → Koraku repo.
2. Tag and publish `koraku` on PyPI from Koraku.
3. Bump `koraku` version in `koraku_cloud/pyproject.toml` / root `pyproject.toml` for Cloud deploys.
4. Cloud production uses `koraku_cloud.app:app` only (not `KORAKU_SERVER_APP=sdk`).

Monorepo layout stays until export is boring; then Cloud can depend on PyPI-only `koraku`.

## Exit criteria (full migration)

- [x] Product chat/auth/tools/health use `koraku.core.product_hooks` (no `koraku_cloud` imports in those paths).
- [x] `is_cloud_profile()` is a thin alias for `product_hooks_active()` only.
- [ ] Cloud server always starts via `koraku_cloud.app` + `bootstrap_cloud()` (operational policy).
- [x] SDK wheel tests pass with hooks cleared (`conftest` + `test_product_hooks`).
