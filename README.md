# Koraku

> Your personal AI buddy and second brain — open-source.

Koraku is a self-hostable AI assistant that **remembers how you work, organizes
your notes and chats into a searchable second brain, and turns repeatable
work into safe automations across your connected apps**. It is a ReAct-style
agent built on a streaming Python backend (FastAPI) and a Next.js web app,
designed to be hosted on a small VM, on a free LLM provider, or with your own
API keys.

- **Repo:** [github.com/meet447/koraku-cloud](https://github.com/meet447/koraku-cloud)
- **License:** [MIT](LICENSE)
- **Security:** [SECURITY.md](SECURITY.md) · **Conduct:** [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- **Contributing:** [CONTRIBUTING.md](CONTRIBUTING.md)
- **Status:** public beta

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/SELF_HOST.md](docs/SELF_HOST.md) | Install (Docker / manual), env, production checklist |
| [docs/SDK.md](docs/SDK.md) | Embed Koraku in Python or TypeScript |
| [docs/DATA_LIFECYCLE.md](docs/DATA_LIFECYCLE.md) | What is stored where (privacy / ops) |
| [docs/SENDBLUE.md](docs/SENDBLUE.md) | iMessage / SMS via SendBlue |

---

## Embed Koraku (SDK)

```bash
pip install -e .              # in-process agent
pip install -e ".[all]"       # API + integrations
```

```python
from koraku import Koraku, KorakuConfig, Tool

agent = Koraku(KorakuConfig(fireworks_api_key="...", llm_provider="fireworks"))
async for event in agent.stream("Summarize this repo"):
    print(event)
```

For web apps, run `koraku-server` and use `@koraku/client` from `packages/koraku-client/`. See **[docs/SDK.md](docs/SDK.md)**.

---

## What Koraku does

- **AI buddy** — streaming chat with tools (web, files, shell, connected apps).
- **Second brain** — `Memory.md` / `Soul.md` plus optional Supabase personalization per organization.
- **Automations** — cron-style jobs using the same agent, with run history.
- **Connected apps** — Gmail, Calendar, Slack, and more via [Composio](https://composio.dev/).
- **iMessage (optional)** — inbound/outbound via [SendBlue](docs/SENDBLUE.md).

## Where tools run

| UI label | `execution_target` | Where tools run |
|----------|-------------------|-----------------|
| **This computer** | `local` / `server` | Host running the Python API |
| **Sandbox** | `cloud` | Isolated [Blaxel](https://blaxel.ai/) VM (your keys) |

**Sandbox** means Blaxel, not a Koraku-operated cloud. Default without Blaxel: **This computer**.

---

## Architecture

```
┌─────────────┐   SSE / JSON via /koraku-api/*   ┌─────────────────────┐
│   Browser   │ ◄──────────────────────────────► │   FastAPI (koraku/) │
│  (Next.js)  │   + Supabase JWT + org header    │                     │
└─────────────┘                                  └──────────┬──────────┘
                                                              │
                ┌─────────────────────────────────────────────┼──────────────────────────┐
                ▼                                             ▼                          ▼
       ┌────────────────┐                            ┌────────────────┐         ┌──────────────────┐
       │   LLM client   │                            │   ReAct loop   │         │  Tool registry   │
       └────────────────┘                            └────────────────┘         │  + Composio      │
                                                                                  │  + Blaxel        │
                                                                                  └──────────────────┘
                                                              │
                                                              ▼
                                                  ┌────────────────────┐
                                                  │ Supabase (optional) │
                                                  │ sessions · chat ·    │
                                                  │ automations · orgs   │
                                                  └────────────────────┘
```

The web app uses **route handlers** under `web/src/app/koraku-api/` (shared logic in `web/src/lib/koraku-backend-proxy.ts` and `koraku-api-routes.ts`) so auth cookies become upstream Bearer tokens without exposing service keys.

### ReAct loop

1. User message → 2. LLM thinks (streamed) → 3. Tool calls → 4. Results fed back → 5. Repeat until final answer.

---

## Quick start

**Fastest:** [Docker Compose](docs/SELF_HOST.md#docker-compose-recommended) → http://localhost:3000

### Backend

```bash
git clone https://github.com/meet447/koraku-cloud.git
cd koraku-cloud
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py   # http://127.0.0.1:8000
```

### Web

```bash
cd web && npm install
cp ../.env.example .env.local   # NEXT_PUBLIC_SUPABASE_* when using auth
npm run dev   # http://127.0.0.1:3000
```

Set `KORAKU_BACKEND_URL` if the API is not on `http://127.0.0.1:8000`.

### Supabase (optional)

```bash
cd web
supabase link --project-ref <your-ref>
npm run db:migrate
```

Without Supabase, Koraku can run in demo mode with local files under `.koraku/`.

---

## Tools

| Tool | Description | API key |
|------|-------------|---------|
| `Bash`, `Glob`, `Grep`, `Read`, `Write`, `Edit` | Workspace file ops | No |
| `WebSearch` | DuckDuckGo | No |
| `WebFetch` | Simple HTML fetch | No |
| `ExaSearch` | Neural search | exa.ai |
| `Firecrawl` / `FirecrawlMap` | JS-aware scrape / map | firecrawl.dev |
| `ComposioRun` | Scoped sub-agent per toolkit | composio.dev |

Add tools in `koraku/tools/registry.py` — see [Extending the agent](#extending-the-agent).

---

## Project layout

```
koraku-cloud/
├── main.py                  # Uvicorn entry
├── koraku/                  # Python package
│   ├── api/                 # HTTP routers
│   ├── agent/               # ReAct loop
│   ├── automations/         # Scheduler + Supabase store
│   ├── integrations/        # Composio, Blaxel, Supabase, SendBlue
│   └── core/                # Config, auth, Redis, startup checks
├── packages/koraku-client/  # TypeScript SSE client
├── web/                     # Next.js app + Supabase migrations
│   └── src/lib/             # BFF proxies, Redis thread cache
├── docs/                    # SELF_HOST, SDK, DATA_LIFECYCLE, SENDBLUE
└── tests/
```

---

## API endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Public liveness (`detached_runs_redis`, LLM configured) |
| `/health/detail` | GET | Ops snapshot (requires `HEALTH_DETAIL_TOKEN`) |
| `/stream` | POST | SSE chat |
| `/runs` | POST | Start detached run |
| `/runs/{id}/stream` | GET | SSE replay / tail |
| `/runs/{id}/status` | GET | Run state |
| `/api/automations` | CRUD | Scheduled automations (org-scoped) |
| `/api/personalization` | GET/PUT | Memory / soul / display name (per org) |
| `/api/composio/*` | … | Connected apps |
| `/sendblue/webhook` | POST | iMessage inbound |

Browser clients should call these via **`/koraku-api/...`** on the Next.js host. Details: [docs/DATA_LIFECYCLE.md](docs/DATA_LIFECYCLE.md).

---

## Configuration

See [`.env.example`](.env.example). Highlights:

| Variable | Description |
|----------|-------------|
| `LLM_PROVIDER` / `FIREWORKS_API_KEY` | Default LLM |
| `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` | Persistence (server only) |
| `REDIS_URL` | Sessions, rate limits, detached runs, multi-worker |
| `HEALTH_DETAIL_TOKEN` | Protects `/health/detail` |
| `SENDBLUE_WEBHOOK_SECRET` | Required when SendBlue is configured |
| `REQUIRE_AUTH_FOR_CHAT` | Default `true` |
| `CORS_ALLOWED_ORIGINS` | Never `*` in production |
| `BLAXEL_CLOUD_SANDBOX_ENABLED` | Cloud sandbox execution |

Production checklist: [docs/SELF_HOST.md#production-checklist](docs/SELF_HOST.md#production-checklist).

---

## Self-hosting

Minimum deploy:

- Python API (long-lived; automations need a running scheduler)
- Next.js host for `web/`
- Supabase for auth + multi-device chat (recommended)
- Redis for multi-worker or durable detached runs

---

## Extending the agent

See [docs/SDK.md](docs/SDK.md).

### Add a tool

```python
from koraku.tools.tool_def import Tool

my_tool = Tool(
    name="MyTool",
    description="Does something useful",
    input_schema={
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
    handler=lambda query: f"Result for {query}",
)
# Append to TOOLS in koraku/tools/registry.py
```

### Custom LLM

Implement a client that emits the normalized streaming event shape used in `koraku/llm/`.

---

## Open source

- [MIT](LICENSE) — use commercially or personally.
- Optional paid integrations (LLM, Blaxel, Composio, Supabase) — all behind env flags.
- [DATA_LIFECYCLE.md](docs/DATA_LIFECYCLE.md) documents storage and third parties.
- Report security issues per [SECURITY.md](SECURITY.md).

---

## License

[MIT](LICENSE) © 2026 Meet Sonawane and Koraku contributors.
