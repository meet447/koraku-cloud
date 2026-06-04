# Koraku SDK

Embeddable ReAct agent for Python apps, HTTP services, and web clients.

## Choose an integration mode

| Your project | Install | How you run Koraku |
|--------------|---------|-------------------|
| **Python script / CLI / bot** | `pip install koraku` | In-process via `Koraku(...)` |
| **Cloud SaaS / backend service** | `pip install "koraku[all]"` | Host with uvicorn, call HTTP/SSE |
| **Web app (React, Next.js, …)** | `@koraku/client` (npm) | Point at your hosted Koraku API |

The Koraku web app in `web/` is a **reference UI** — not required for embedding.

## Configuration layers

| Layer | Module | What it loads |
|-------|--------|----------------|
| **SDK** | `koraku.core.sdk_settings.SdkSettings` | LLM keys, tools, Composio, local/cloud execution target, filesystem memory |
| **Cloud** | `koraku_cloud.cloud_settings.CloudSettings` | Supabase, auth, Redis sessions, Blaxel, automations, SendBlue |

Embedders use **`KorakuConfig` / `SdkSettings` only** — no Supabase env required. This monorepo’s product server calls `koraku_cloud.bootstrap.bootstrap_cloud()` on startup to bind both layers.

The SDK is **not** tailored for Koraku Cloud — Cloud embeds the SDK and adds product settings on top.

```python
from koraku import Koraku, KorakuConfig

# Local-first (only an LLM key required)
agent = Koraku(KorakuConfig(fireworks_api_key="...", workspace="."))
```

Optional SDK plugins: Composio (`COMPOSIO_API_KEY`), web tools (`EXA_API_KEY`, `FIRECRAWL_API_KEY`). Cloud-only: Supermemory, Blaxel, Supabase (see repo `.env.example`).

## Auth backends (embed / SaaS)

Set `AUTH_BACKEND` (or `KORAKU_AUTH_BACKEND`) on the server:

| Backend | Env | Use when |
|---------|-----|----------|
| `supabase` (default) | `SUPABASE_JWT_SECRET` or JWKS | Koraku web app + multi-user |
| `api_key` | `KORAKU_API_KEY` | Service-to-service, single-tenant SaaS |
| `none` | — | Local OSS with `REQUIRE_AUTH_FOR_CHAT=false` |

Clients send `Authorization: Bearer <token>` for `supabase` and `api_key`.

## SDK server vs Cloud server

| App module | Routes | Use |
|------------|--------|-----|
| `koraku.server_sdk` | `/health`, `/stream`, `/api/composio/*`, `/api/chat-models` | Embedders, self-host without Supabase |
| `koraku_cloud.app` | SDK routes + `/runs`, `/api/personalization`, automations, memory graph, SendBlue, workspace | Koraku Cloud product only |

Supabase chat history and personalization load only when the Cloud layer is bound (see `koraku/api/chat_hydration.py` and `koraku_cloud.bootstrap`).

## Session store and detached runs (multi-worker)

| Backend | Env | Use when |
|---------|-----|----------|
| `memory` | — | Single uvicorn worker / dev |
| `redis` | `REDIS_URL` | Multiple API replicas |

Set `SESSION_STORE_BACKEND=redis` when using `REDIS_URL` so chat sessions survive load balancing.

Detached runs (`POST /runs`, `GET /runs/{id}/stream`):

- `DETACHED_RUN_STORE_BACKEND=auto` (default) uses Redis when `REDIS_URL` is reachable (`detached_runs_redis` on `GET /health`).
- Without Redis, buffers are in-process — use sticky sessions or a single worker.

Ops snapshot: `GET /health/detail` with `HEALTH_DETAIL_TOKEN`.

## Publishing

Tag a release (`git tag v0.2.0 && git push origin v0.2.0`) to trigger `.github/workflows/release.yml`:

- **PyPI** — requires GitHub environment `pypi` with [trusted publishing](https://docs.pypi.org/trusted-publishers/)
- **npm** — requires GitHub environment `npm` with `NPM_TOKEN` secret

## Install

```bash
# Core SDK only (in-process agent)
pip install -e .

# Full self-hosted stack (FastAPI server + integrations)
pip install -e ".[all]"
```

## Python — in-process embed

```python
from koraku import Koraku, KorakuConfig, Tool

async def my_tool(query: str) -> str:
    return f"Echo: {query}"

agent = Koraku(
    KorakuConfig(fireworks_api_key="...", llm_provider="fireworks"),
    tools=[Tool(name="Echo", description="Echo text", input_schema={
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    }, handler=my_tool)],
)

async for event in agent.stream("Use Echo on hello"):
    print(event)
```

See [`examples/embed_python.py`](../examples/embed_python.py).

## Python — configure process defaults

```python
from koraku import configure, KorakuConfig

configure_sdk(KorakuConfig(fireworks_api_key="...").to_sdk_settings())
# or: configure(KorakuConfig(...).to_settings())  # merged view
```

## HTTP — remote agent service

Run the **SDK server** (no Supabase product routes):

```bash
KORAKU_SERVER_APP=sdk uvicorn koraku.server_sdk:app --reload
# monorepo Cloud API: ./scripts/run-api.sh  →  koraku_cloud.app:app
```

Then call `POST /stream` from any language. Optional: `GET /health`, Composio routes when `COMPOSIO_API_KEY` is set.

Koraku Cloud uses `koraku_cloud.app:app` with personalization, automations, detached runs, and Supabase-backed chat — not part of the public SDK wheel.

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

## Package layout

| Package | Install | Purpose |
|---------|---------|---------|
| `koraku` | `pip install koraku` | Agent core, tools, LLM (`Koraku`, `Tool`, `Agent`) |
| `koraku[server]` | `pip install "koraku[server]"` | SDK FastAPI app (`/health`, `/stream`, Composio); run with uvicorn |
| `koraku[composio]` | optional | Connected-app toolkits |
| `koraku[blaxel]` | optional | Cloud sandbox execution |
| `koraku[all]` | `pip install "koraku[all]"` | Full self-hosted stack |
| `@koraku/client` | `packages/koraku-client` | TypeScript SSE client for web/cloud apps |
| `koraku_cloud` | monorepo only (not on PyPI) | Koraku Cloud product: Supabase routes, automations, detached runs |

Product code lives in `koraku_cloud/`. The PyPI wheel ships `koraku` only. See [PACKAGING.md](./PACKAGING.md).

## Migration from `src/`

The old `import src.agent` layout is removed. Use `koraku` instead:

```python
# before
from src.agent import Agent

# after
from koraku import Agent
# or
from koraku.agent import Agent
```
