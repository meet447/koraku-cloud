# Koraku roadmap

Koraku is built in two **products**:

1. **OSS self-host** — run the webapp and API yourself; tools on **your computer** or an optional **Blaxel sandbox**.
2. **Koraku Cloud** (later) — hosted, multi-tenant, durable detached runs, premium surfaces.

See [PRODUCT.md](PRODUCT.md) for how this differs from the chat toggle labeled **Sandbox** (Blaxel), which is **not** Koraku Cloud.

## Phase 1 — OSS self-host (now)

**Goal:** Clone → configure → chat with tools in under 30 minutes. No Koraku-operated services required.

### Where tools run (OSS only)

| Choice | `execution_target` | Notes |
|--------|-------------------|--------|
| **This computer** | `local` / `server` | Full tools on the API host (your desktop when self-hosting) |
| **Sandbox (Blaxel)** | `cloud` | Isolated VM; requires `BLAXEL_*` keys |

### In scope / out of scope

| In scope | Out of scope (Koraku Cloud — Phase 2) |
|----------|----------------------------------------|
| Self-host Python API + Next.js UI | Multi-tenant orgs / billing |
| Supabase auth (optional) | Managed Koraku-hosted API |
| This computer + optional Blaxel sandbox | Durable detached runs across replicas |
| Optional Composio connections | Mobile apps |
| Embeddable `koraku` SDK + `@koraku/client` | iMessage / SMS bridges |
| Docker Compose runbook | Per-tenant quotas / usage metering |

**Success:** Someone runs Docker Compose (or manual install), picks **This computer** or **Sandbox**, and completes a real agent turn without your help.

See [SELF_HOST.md](SELF_HOST.md).

## Phase 2 — Koraku Cloud (premium, later)

**Goal:** Same agent core, plus a **hosted control plane** for production SaaS.

Planned capabilities (not committed to a date):

1. **Multi-tenant control plane** — org/workspace IDs on auth, sessions, runs, and storage
2. **Durable detached runs** — Redis (or queue) run store + SSE pub/sub (no sticky sessions)
3. **Managed deploy** — Koraku-operated API + web; policies for sandboxes and quotas
4. **Mobile clients** — `@koraku/client` + native auth
5. **Messaging** — iMessage/SMS/webhook adapters → async agent jobs

Phase 2 **imports** the `koraku` package; it does not fork the ReAct loop.

## SDK layering

```
koraku (PyPI)          Agent, Tool, LLM, Koraku facade
    ↑
koraku-server          FastAPI, SSE, optional extras [composio, blaxel]
    ↑
@koraku/client (npm)   SSE client for any web/mobile app
    ↑
web/ (OSS)             Reference UI — self-host only
    ↑
cloud/ (future)        Koraku Cloud control plane — not in OSS repo yet
```

### Interfaces to keep stable

| Interface | OSS self-host | Koraku Cloud |
|-----------|---------------|--------------|
| Auth | `supabase` / `api_key` / `none` | + org claims, tenant API keys |
| Session store | `memory` / `redis` | Redis with tenant prefix |
| Run store | in-process (detached) | Redis pub/sub |
| HTTP + SSE | `POST /stream`, `koraku.*` events | Same contract, versioned |

## How to contribute

- **Phase 1:** install friction, UX polish, docs, self-host defaults, bugs in `web/` and `koraku-server`
- **Phase 2:** design docs and interfaces until `cloud/` opens; no premature multi-tenant code in OSS paths
