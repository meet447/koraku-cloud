# Koraku product split

Koraku is two products that share the same **agent core** (`koraku` package), not one product with a “cloud mode” toggle.

## OSS / self-host (Phase 1)

You run the Python API and Next.js UI yourself. **Koraku does not operate any servers for you.**

Where **tools** run (files, shell, grep) is a per-chat choice:

| UI label | API `execution_target` | Where tools run |
|----------|------------------------|-----------------|
| **This computer** | `local` (or `server`) | The machine hosting the Koraku API — your laptop when you self-host |
| **Sandbox** | `cloud` | An isolated [Blaxel](https://blaxel.ai/) VM you configure with `BL_*` keys |

There is **no** “Koraku Cloud desktop” in OSS. “Cloud” in the API only means **Blaxel sandbox**, not the hosted Koraku product.

Typical setups:

- **No Blaxel** → use **This computer** only.
- **With Blaxel** → choose **Sandbox** for isolation, or **This computer** for speed and direct disk access.

A future **linked desktop app** may route `local` to another machine; today `local` runs in-process on the API host.

## Koraku Cloud (Phase 2 — premium, separate)

**Hosted by Koraku** (or your own control plane): multi-tenant workspaces, billing, managed auth, **durable detached runs** across API replicas (Redis run store + SSE pub/sub), mobile/messaging surfaces, and sandboxes operated as part of the service.

Phase 2 is **not** “turn on Blaxel in `.env`”. It is a separate deploy and repo area (`cloud/` when we open it) that **imports** `koraku` and `@koraku/client` without forking the ReAct loop.

| | OSS self-host | Koraku Cloud |
|---|---------------|--------------|
| Who runs the API | You | Koraku (managed) |
| Tenants / orgs | Single-user / your Supabase | Multi-tenant control plane |
| Detached runs | In-process (same worker) | Durable, cross-replica |
| Tool surfaces | This computer + optional Blaxel | Managed sandboxes + policies |
| Billing | Your keys (LLM, Blaxel, etc.) | Subscription / usage |

See [ROADMAP.md](ROADMAP.md) for phase checklist and [SELF_HOST.md](SELF_HOST.md) to run OSS today.
