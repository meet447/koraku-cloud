# Koraku SDK

Embeddable ReAct agent for Python apps, HTTP services, and web clients.

## Choose an integration mode

| Your project | Install | How you run Koraku |
|--------------|---------|-------------------|
| **Python script / CLI / bot** | `pip install koraku` | In-process via `Koraku(...)` |
| **Cloud SaaS / backend service** | `pip install "koraku[all]"` | Host `koraku-server`, call HTTP/SSE |
| **Web app (React, Next.js, …)** | `@koraku/client` (npm) | Point at your hosted Koraku API |

The Koraku web app in `web/` is a **reference UI** — not required for embedding.

## Auth backends (embed / SaaS)

Set `AUTH_BACKEND` (or `KORAKU_AUTH_BACKEND`) on the server:

| Backend | Env | Use when |
|---------|-----|----------|
| `supabase` (default) | `SUPABASE_JWT_SECRET` or JWKS | Koraku web app + multi-user |
| `api_key` | `KORAKU_API_KEY` | Service-to-service, single-tenant SaaS |
| `none` | — | Local OSS with `REQUIRE_AUTH_FOR_CHAT=false` |

Clients send `Authorization: Bearer <token>` for `supabase` and `api_key`.

## Session store (multi-worker)

| Backend | Env | Use when |
|---------|-----|----------|
| `memory` (default) | — | Single uvicorn worker / dev |
| `redis` | `UPSTASH_REDIS_REST_URL` + `UPSTASH_REDIS_REST_TOKEN` | Multiple API replicas |

Set `SESSION_STORE_BACKEND=redis` so chat sessions survive load-balanced routing.
Detached run buffers remain in-process (subscribe still needs sticky sessions or same worker).

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

configure(KorakuConfig(fireworks_api_key="...").to_settings())
```

## HTTP — remote agent service

Run the server (`python main.py` or `koraku-server`), then call `POST /stream` from any language.

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
| `koraku[server]` | `pip install "koraku[server]"` | FastAPI app + `koraku-server` CLI |
| `koraku[composio]` | optional | Connected-app toolkits |
| `koraku[blaxel]` | optional | Cloud sandbox execution |
| `koraku[all]` | `pip install "koraku[all]"` | Full self-hosted stack |
| `@koraku/client` | `packages/koraku-client` | TypeScript SSE client for web/cloud apps |

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
