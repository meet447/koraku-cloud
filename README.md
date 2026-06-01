# Koraku

> Your personal AI buddy and second brain — open-source.

Koraku is a self-hostable AI assistant that **remembers how you work, organizes
your notes and chats into a searchable second brain, and turns repeatable
work into safe automations across your connected apps**. It is a ReAct-style
agent built on a streaming Python backend (FastAPI) and a Next.js web app,
designed to be hosted on a small VM, on a free LLM provider, or with your own
API keys.

The project is **MIT-licensed** ([LICENSE](LICENSE)) and welcomes
contributions — see [CONTRIBUTING.md](CONTRIBUTING.md).

- Source: **github.com/meet447/koraku**
- License: [MIT](LICENSE)
- Security: [SECURITY.md](SECURITY.md) · Conduct:
  [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- Status: **public beta**
- **SDK:** embed the agent in Python apps or call it over HTTP — see [docs/SDK.md](docs/SDK.md)

---

## Embed Koraku (SDK)

Koraku ships as an **embeddable Python package** and an optional **TypeScript SSE client**:

```bash
# Core agent (in-process)
pip install -e .

# Self-hosted API + integrations
pip install -e ".[all]"
```

```python
from koraku import Koraku, KorakuConfig, Tool

agent = Koraku(KorakuConfig(fireworks_api_key="...", llm_provider="fireworks"))
async for event in agent.stream("Summarize this repo"):
    print(event)
```

For web/cloud apps, run `koraku-server` and use `@koraku/client` from
`packages/koraku-client/`. Full guide: **[docs/SDK.md](docs/SDK.md)**.

---

## What Koraku does

- **AI buddy** — chats with you, streams its thinking, and uses tools
  (web search, files, shell, your connected apps) to actually get things
  done, not just answer.
- **Second brain** — every chat can write to your personal
  `Memory.md` and `Soul.md` (preferences and persona) so the agent remembers
  what you like, how you work, and what matters across sessions.
- **Automations** — turn any prompt into a scheduled job (cron-style) backed
  by the same agent, with a UI to create, edit, pause, and inspect runs.
- **Connected apps** — link Gmail, Calendar, Drive, Slack, and dozens more via
  [Composio](https://composio.dev/); the agent can request scoped sub-tools
  per toolkit instead of dumping every API into the prompt.
- **Three places to run your agent** — see "Where the agent runs" below.

## Where the agent runs (OSS self-host)

The **brain** (LLM + ReAct loop) runs in the Python API. The **hands** (file and
shell tools) run in one of two places you pick per chat — this is **not** the
same as **Koraku Cloud** (hosted multi-tenant product; see [docs/PRODUCT.md](docs/PRODUCT.md)).

| UI (OSS) | `execution_target` | Where tools run |
|----------|-------------------|-----------------|
| **This computer** | `local` / `server` | The machine running the Koraku API (your desktop when you self-host) |
| **Sandbox** | `cloud` | Isolated [Blaxel](https://blaxel.ai/) VM (your Blaxel keys; not Koraku-operated) |

- **This computer** — read/write your repos, run bash, use your PATH. Default when Blaxel is not configured.
- **Sandbox** — fresh VM per session; nothing touches your main disk. Set `BLAXEL_CLOUD_SANDBOX_ENABLED` and `BL_*` in `.env`.

A future linked desktop app may route `local` to another machine; today `local` uses the API host workspace.

---

## Architecture

```
┌─────────────┐      SSE (text/event-stream)      ┌─────────────────────┐
│   Browser   │ ◄────────────────────────────────► │   FastAPI server    │
│  (Next.js)  │                                    │   (Python · koraku/)   │
└─────────────┘                                    └──────────┬──────────┘
                                                              │
                ┌─────────────────────────────────────────────┼─────────────────────────────────────────┐
                ▼                                             ▼                                         ▼
       ┌────────────────┐                            ┌────────────────┐                       ┌──────────────────┐
       │   LLM client   │                            │   ReAct loop   │                       │  Tool registry   │
       │ Fireworks /    │◄──────────────────────────►│  koraku/agent  │◄─────────────────────►│  koraku/tools    │
       │ Anthropic /    │                            └────────┬───────┘                       │  + Composio      │
       │ OpenAI-compat  │                                     │                               │  + Blaxel VM     │
       └────────────────┘                                     ▼                               └──────────────────┘
                                                  ┌────────────────────┐
                                                  │  Second-brain      │
                                                  │  • Memory.md       │
                                                  │  • Soul.md         │
                                                  │  • Supabase chat   │
                                                  │  • Automations DB  │
                                                  └────────────────────┘
```

### ReAct loop

1. **User** sends a message
2. **LLM** thinks step-by-step (streamed live as `thinking_delta` events)
3. **LLM** decides to use a **tool** (`tool_use` events with incremental JSON)
4. **Tool** executes on the chosen target (cloud sandbox / linked desktop /
   server) and the result is fed back
5. **LLM** thinks again with the new context, optionally updates `Memory.md`
6. Repeat until the LLM produces a **final answer**

---

## Quick start

**Fastest path:** [Docker Compose](docs/SELF_HOST.md#docker-compose-recommended) — `docker compose up --build` → http://localhost:3000

### 1. Backend (Python API)

```bash
git clone https://github.com/meet447/koraku.git
cd koraku

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — at minimum pick an LLM provider (Fireworks recommended, or add
# OpenAI-compatible providers via LLM_OPENAI_COMPAT_IDS)

python main.py
# API on http://127.0.0.1:8000  ·  health: GET /health
```

### 2. Web app (Next.js)

```bash
cd web
npm install
cp ../.env.example .env.local  # then set NEXT_PUBLIC_SUPABASE_* if using auth
npm run dev
# UI on http://127.0.0.1:3000
```

The web app proxies SSE and APIs to the Python backend via `next.config.ts`
rewrites; override the backend with `KORAKU_BACKEND_URL` if needed.

### 3. (Optional) Supabase auth + persistence

```bash
cd web
supabase link --project-ref <your-ref>
npm run db:migrate
```

Migrations live in `web/supabase/migrations/`. Without Supabase, Koraku still
runs single-user with files on disk under `.koraku/`.

---

## Tools

Built-in tools the agent can call:

| Tool          | Description                                                  | API key |
|---------------|--------------------------------------------------------------|---------|
| `Bash`        | Execute shell commands in the workspace                      | No      |
| `Glob`        | Find files matching patterns (`*.py`, `src/**/*.ts`)         | No      |
| `Grep`        | Search file contents with regex                              | No      |
| `Read`        | Read file contents with line numbers                         | No      |
| `Write`       | Create or overwrite files                                    | No      |
| `Edit`        | Replace text in files (exact match)                          | No      |
| `WebSearch`   | Search the web via DuckDuckGo                                | No      |
| `WebFetch`    | Lightweight page fetch for simple HTML                       | No      |
| `ExaSearch`   | Neural search — semantically relevant content                | exa.ai  |
| `Firecrawl`   | JS-aware scraping — handles SPAs, dynamic content            | firecrawl.dev |
| `FirecrawlMap`| Crawl a site to discover all linked URLs                     | firecrawl.dev |
| `ComposioRun` | Spawns a scoped sub-agent for a connected toolkit (Gmail, …) | composio.dev |

Add your own by appending to the tool registry — see
[Extending the agent](#extending-the-agent).

---

## Project layout

```
koraku/
├── main.py                  # Uvicorn entry (loads koraku.server:app)
├── requirements.txt
├── .env.example
├── LICENSE                  # MIT
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── docs/                    # SDK.md, DATA_LIFECYCLE.md, PUBLIC_BETA_RUNBOOK.md
├── examples/                # embed_python.py — minimal in-process SDK usage
├── tests/                   # Pytest suite (mirrors koraku/ domains)
│
├── koraku/                  # Python package (`pip install -e .`)
│   ├── sdk.py               # Koraku + KorakuConfig embed facade
│   ├── server.py            # FastAPI app factory + routes (optional extra)
│   ├── api/                 # HTTP routers (chat, runs, automations, …)
│   ├── agent/               # ReAct loop, sessions, runtime context
│   ├── llm/                 # Providers, streaming normalization
│   ├── tools/               # Tool registry, policy, builtins
│   ├── integrations/        # Composio, Blaxel, Supabase (optional extras)
│   ├── streaming/           # Koraku SSE envelope
│   ├── workspace/           # Paths, sandbox context, brain files
│   ├── automations/         # Saved automation tools + scheduler
│   └── core/                # Settings, auth, redact
│
├── packages/
│   └── koraku-client/       # `@koraku/client` TypeScript SSE SDK
│
└── web/                     # Next.js 15 reference app (npm run dev on :3000)
    └── src/
        ├── app/             # Routes + koraku-api BFF proxies
        ├── components/
        ├── hooks/
        └── lib/
```

---

## API endpoints

| Endpoint                | Method | Description                                      |
|-------------------------|--------|--------------------------------------------------|
| `/`                     | GET    | Service metadata                                 |
| `/health`               | GET    | Health, mode, configured providers               |
| `/stream`               | POST   | SSE streaming chat                               |
| `/runs`                 | POST   | Start a detached run (resume after disconnect)   |
| `/runs/{id}/stream`     | GET    | Subscribe to a detached run's SSE                |
| `/runs/{id}/status`     | GET    | `running` · `completed` · `not_found`            |
| `/automations`          | CRUD   | Saved scheduled automations                      |
| `/personalization`      | CRUD   | `Memory.md`, `Soul.md`, display name             |
| `/composio/*`           | …      | List + link connected apps                       |

See [`docs/DATA_LIFECYCLE.md`](docs/DATA_LIFECYCLE.md) for what each endpoint
reads and writes.

---

## Configuration

Set via environment variables or `.env`. Highlights — see
[`.env.example`](.env.example) for the full list:

| Variable                       | Default        | Description                                |
|--------------------------------|----------------|--------------------------------------------|
| `LLM_PROVIDER`                 | `fireworks`    | Default provider id (`fireworks`, `anthropic`, or any registered OpenAI-compat id) |
| `LLM_OPENAI_COMPAT_IDS`        | —              | Comma-separated OpenAI-compatible providers (`openai,groq,ollama`, …) |
| `FIREWORKS_API_KEY`            | —              | Fireworks key (recommended provider)       |
| `ANTHROPIC_API_KEY`            | —              | Claude API key                             |
| `CUSTOM_BASE_URL`              | —              | Registers provider id `custom` when set  |
| `EXA_API_KEY` / `FIRECRAWL_API_KEY` | —         | Premium research tools                     |
| `COMPOSIO_API_KEY`             | —              | Connected-app toolkits                     |
| `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` | —    | Persistence + automations          |
| `SUPABASE_JWT_SECRET`          | —              | HS256 JWT verification (else JWKS)         |
| `BLAXEL_CLOUD_SANDBOX_ENABLED` | `false`        | Enable `execution_target=cloud` sandboxes  |
| `REQUIRE_AUTH_FOR_CHAT`        | `true`         | Require a signed-in user for chat          |
| `CORS_ALLOWED_ORIGINS`         | localhost:3000 | Comma-separated browser origins            |
| `CHAT_RATE_LIMIT_PER_MINUTE`   | `12`           | Per-user soft rate limit                   |
| `PORT`                         | `8000`         | API port                                   |

---

## Self-hosting

Koraku is designed to be self-hosted. The minimum useful deploy is:

- One long-lived VM/container for the Python API (1 GB RAM is fine for
  single-user)
- A Next.js host (Vercel, Fly, your own VM) for `web/`
- A Supabase project for auth, chat history, and automations
- Optional: Upstash Redis for cross-worker rate limits, Blaxel for cloud
  sandboxes, Composio for connected apps

See [`docs/PUBLIC_BETA_RUNBOOK.md`](docs/PUBLIC_BETA_RUNBOOK.md) for the
production checklist (env vars, CORS, rate limits, degraded modes, recovery).

---

## Extending the agent

See [docs/SDK.md](docs/SDK.md) for embedding Koraku in other Python, web, and cloud projects.

### Add a new tool

```python
# koraku/tools/registry.py (or a new file imported by it)
from koraku.tools.tool_def import Tool

async def _my_tool(query: str) -> str:
    return f"Result for {query}"

my_tool = Tool(
    name="MyTool",
    description="Does something useful",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to query"},
        },
        "required": ["query"],
    },
    handler=_my_tool,
)

TOOLS.append(my_tool)
```

The agent discovers it automatically through `get_tool_schemas()`.

### Use a different LLM provider

Replace or extend `koraku/llm/client.py` with your own client (Ollama, Bedrock,
vLLM, …) as long as it yields events in the normalized Anthropic-style shape:

```python
{"type": "message_start",        "message": {...}}
{"type": "content_block_start",  "index": N, "content_block": {...}}
{"type": "content_block_delta",  "index": N, "delta": {...}}
{"type": "content_block_stop",   "index": N}
{"type": "message_delta",        "delta": {...}}
{"type": "message_stop",         "message": {...}}
```

---

## Open-source principles

Koraku is built to be a project the community can actually use, audit, and
contribute to:

- **Permissive license.** [MIT](LICENSE) — use it personally or commercially.
- **No proprietary lock-in.** Every paid integration (Anthropic, Fireworks,
  Blaxel, Composio, Supabase, Exa, Firecrawl) is **optional** and behind a
  config flag. Multiple OpenAI-compatible providers can be registered side by side.
- **Self-hostable by default.** No required Koraku-controlled service; you
  bring your own keys and your own host.
- **Transparent data lifecycle.** [`docs/DATA_LIFECYCLE.md`](docs/DATA_LIFECYCLE.md)
  documents exactly what is stored where, including third parties.
- **Welcoming community.** Code of Conduct ([CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md))
  and clear contribution path ([CONTRIBUTING.md](CONTRIBUTING.md)).
- **Coordinated security.** Private disclosure process in
  [SECURITY.md](SECURITY.md).
- **Public roadmap & issues.** All work happens on GitHub — file bugs,
  propose features, send PRs.

---

## Contributing

Bug reports, ideas, new tools, integrations, and UI polish are all welcome.
Start with [CONTRIBUTING.md](CONTRIBUTING.md) and the open issues.

## License

[MIT](LICENSE) © 2026 Meet Sonawane and Koraku contributors.
# koraku-cloud
