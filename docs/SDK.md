# Koraku SDK

Embeddable ReAct agent for Python apps, HTTP services, and web clients.

**Open-source home:** [github.com/meet447/Koraku](https://github.com/meet447/Koraku) — `pip install koraku` and PyPI releases are published from that repo. This file is the export source; product-specific server behavior lives in **koraku-cloud** (`koraku_cloud/`).

## Choose an integration mode

| Your project | Install | How you run Koraku |
|--------------|---------|-------------------|
| **Python script / CLI / bot** | `pip install koraku` | In-process via `Koraku(...)` |
| **Self-hosted HTTP API** | `pip install "koraku[server]"` or `[all]` | `uvicorn koraku.server_sdk:app` |
| **Web app (React, Next.js, …)** | `@koraku/client` (npm) | Point at your Koraku API base URL |

## Configuration layers

| Layer | Module | What it loads |
|-------|--------|----------------|
| **SDK** | `koraku.core.sdk_settings.SdkSettings` | LLM keys, tools, Composio, execution target, filesystem memory |
| **Cloud** (optional) | `koraku.inert_cloud_settings.CloudSettings` / `koraku_cloud` in monorepo | Supabase, auth, Redis, Blaxel, automations, SendBlue |

Embedders use **`KorakuConfig` / `SdkSettings` only** — no Supabase required. Koraku Cloud calls `koraku_cloud.bootstrap.bootstrap_cloud()` to bind the product layer.

```python
from koraku import Koraku, KorakuConfig

agent = Koraku(KorakuConfig(fireworks_api_key="...", workspace="."))
```

Optional: Composio (`COMPOSIO_API_KEY`), web tools (`EXA_API_KEY`, `FIRECRAWL_API_KEY`).

## Auth backends (HTTP server)

| Backend | Env | Use when |
|---------|-----|----------|
| `supabase` | `SUPABASE_JWT_SECRET` | Multi-user apps with Supabase Auth |
| `api_key` | `KORAKU_API_KEY` | Service-to-service |
| `none` | — | Local dev with `REQUIRE_AUTH_FOR_CHAT=false` |

## SDK server vs Cloud server

| App module | Routes | Use |
|------------|--------|-----|
| `koraku.server_sdk` | `/health`, `/stream`, `/api/composio/*`, `/api/chat-models` (auth when `REQUIRE_AUTH_FOR_CHAT=true`) | Embedders, self-host without Supabase |
| `koraku_cloud.app` | SDK routes + automations, personalization, workspace, SendBlue | Koraku Cloud only (not in PyPI wheel) |

## Session store and detached runs

| Backend | Env | Use when |
|---------|-----|----------|
| `memory` | — | Single worker / dev |
| `redis` | `REDIS_URL` | Multiple API replicas |

Detached runs need Redis for multi-worker (`DETACHED_RUN_STORE_BACKEND=auto`).

## Install

From [Koraku](https://github.com/meet447/Koraku) or this monorepo during development:

```bash
pip install koraku
# or
pip install -e ".[all]"   # monorepo / Koraku clone
```

## Python — in-process

```python
from koraku import Koraku, KorakuConfig

agent = Koraku(KorakuConfig(fireworks_api_key="...", llm_provider="fireworks"))
async for event in agent.stream("Summarize this repo"):
    print(event)
```

See [`examples/embed_python.py`](../examples/embed_python.py).

## HTTP — SDK server

```bash
uvicorn koraku.server_sdk:app --reload --port 8000
```

Monorepo Cloud API: `./scripts/run-api.sh` → `koraku_cloud.app:app`.

## TypeScript / web

```bash
cd packages/koraku-client && npm install && npm run build
```

```typescript
import { KorakuClient } from "@koraku/client";

const client = new KorakuClient("http://127.0.0.1:8000", {
  Authorization: "Bearer <token>",
});
for await (const inner of client.streamInnerEvents("Hello")) {
  console.log(inner);
}
```

## Packages

| Package | Where | Purpose |
|---------|-------|---------|
| `koraku` | PyPI / Koraku repo | Agent core, tools, LLM |
| `koraku[server]` | PyPI | FastAPI `/health`, `/stream` |
| `@koraku/client` | npm (Koraku repo) | TypeScript SSE client |
| `koraku_cloud` | koraku-cloud only | Product server (not on PyPI) |

See [PACKAGING.md](./PACKAGING.md) for monorepo layout and `./scripts/export-sdk-oss-repo.sh`.
