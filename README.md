# Koraku

> Automate your work with natural language.

**Koraku** is an AI workspace in the cloud. Connect the apps you already use — Gmail, Notion, Linear, Calendar, and dozens more — then describe outcomes in plain language. Agents pull live context, draft results in your workspace, and ask before sending email, posting to chat, or changing records in connected tools.

This repository (**koraku-cloud**) is the product monorepo: the Next.js web app, Supabase-backed persistence, automations, and the `koraku_cloud` API layer.

The **open-source embeddable SDK** (`koraku`, `@koraku/client`) lives separately at [github.com/meet447/Koraku](https://github.com/meet447/Koraku). This repo vendors the same `koraku/` sources for Cloud development and syncs them via `./scripts/export-sdk-oss-repo.sh`.

- **Repo:** [github.com/meet447/koraku-cloud](https://github.com/meet447/koraku-cloud)
- **License:** [MIT](LICENSE)
- **Security:** [SECURITY.md](SECURITY.md) · **Conduct:** [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- **Contributing:** [CONTRIBUTING.md](CONTRIBUTING.md)

## What Koraku is for

Koraku is built for people who want agent work that feels native — not one-off chats that forget context or scripts you have to maintain.

| Goal | How Koraku helps |
|------|------------------|
| **One place for agent work** | Hosted chat, workspace files, automations, and run history in your account |
| **Your stack, connected** | OAuth to 35+ apps; context stays in Koraku instead of scattered across sessions |
| **Natural language, not scripts** | Describe outcomes; agents follow personalization and memory on every run |
| **You stay in control** | Approval gates before sensitive actions; revoke integrations anytime |
| **Pick up anywhere** | Web app, scheduled automations, and optional iMessage / SMS |

Typical workflows: morning briefs across calendar and inbox, research that lands as workspace notes, follow-up drafts that wait for your OK, and a second brain that remembers tone and preferences across chats.

## How it works

1. **Connect** — Link Gmail, Notion, Linear, and the rest once in Settings.
2. **Instruct** — Describe what you want in plain language; no scripts required.
3. **Review & run** — Drafts land in your cloud workspace; Koraku asks before high-impact actions.

## What’s in this repo

- **AI buddy** — Streaming chat with tools (web search, files, shell, connected apps).
- **Second brain** — Learned memory plus personalization (name, tone, persona) per organization.
- **Agent workspace** — Cloud folder for drafts, exports, and agent-created files.
- **Automations** — Cron-style jobs and event triggers via Composio, with run history.
- **Connected apps** — Gmail, Calendar, Slack, Notion, Linear, and more via [Composio](https://composio.dev/).
- **iMessage (optional)** — Inbound/outbound messaging via [SendBlue](docs/SENDBLUE.md).
- **Embeddable SDK** — `koraku/` and `packages/koraku-client/` (exported to the open-source Koraku repo).

## Koraku Cloud vs open-source SDK

| | **Koraku Cloud** (this repo) | **Koraku SDK** ([meet447/Koraku](https://github.com/meet447/Koraku)) |
|--|------------------------------|------------------------------------------------------------------------|
| **What** | Full product: web UI, auth, orgs, automations | Embeddable ReAct agent for Python, HTTP, and web clients |
| **Install** | Self-host with Docker or manual setup (below) | `pip install koraku` · `@koraku/client` on npm |
| **Persistence** | Supabase (chat, personalization, automations) | Local `.koraku/` files or bring your own backend |
| **Use when** | You want the Koraku app experience | You’re building your own app on top of the agent |

See [docs/SDK.md](docs/SDK.md) and [docs/PACKAGING.md](docs/PACKAGING.md) for integration details.

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/SELF_HOST.md](docs/SELF_HOST.md) | Install (Docker / manual), env, production checklist |
| [docs/SDK.md](docs/SDK.md) | Embed Koraku in Python or TypeScript |
| [docs/PACKAGING.md](docs/PACKAGING.md) | SDK vs Cloud packages, OSS export, PyPI |
| [docs/DATA_LIFECYCLE.md](docs/DATA_LIFECYCLE.md) | What is stored where (privacy / ops) |
| [docs/SENDBLUE.md](docs/SENDBLUE.md) | iMessage / SMS via SendBlue |

## Quick start

**Fastest:** [Docker Compose](docs/SELF_HOST.md#docker-compose-recommended) → http://localhost:3000

### Backend

```bash
git clone https://github.com/meet447/koraku-cloud.git
cd koraku-cloud
cp .env.example .env
./scripts/install-monorepo.sh
./scripts/run-api.sh            # http://127.0.0.1:8000
```

Use **only** `koraku-cloud/.venv`. Remove stray envs: `./scripts/cleanup-extra-venvs.sh`

SDK-only API (no Supabase product routes): `KORAKU_SERVER_APP=sdk ./scripts/run-api.sh`

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

Koraku Cloud requires Supabase for signed-in users (personalization, chat history, skills). SDK-only mode (`KORAKU_SERVER_APP=sdk`) may still use local `.koraku/` files — see [docs/SDK.md](docs/SDK.md).

## Where tools run

| UI label | `execution_target` | Where tools run |
|----------|-------------------|-----------------|
| **This computer** | `local` / `server` | Host running the Python API |
| **Sandbox** | `cloud` | Isolated [Blaxel](https://blaxel.ai/) VM (your keys) |

**Sandbox** means Blaxel, not a Koraku-operated cloud. Default without Blaxel: **This computer**.

## Architecture

```
┌─────────────┐   SSE / JSON via /koraku-api/*   ┌──────────────────────────┐
│   Browser   │ ◄──────────────────────────────► │  koraku_cloud (FastAPI) │
│  (Next.js)  │   + Supabase JWT + org header    │  embeds koraku SDK        │
└─────────────┘                                  └──────────┬───────────────┘
                                                            │
                ┌───────────────────────────────────────────┼──────────────────┐
                ▼                                           ▼                  ▼
       ┌────────────────┐                          ┌────────────────┐  ┌──────────────┐
       │   LLM client   │                          │   ReAct loop   │  │ Tool registry │
       └────────────────┘                          └────────────────┘  └──────────────┘
                                                            │
                                                            ▼
                                                ┌────────────────────┐
                                                │ Supabase (optional) │
                                                └────────────────────┘
```

The web app proxies API traffic through **`web/src/app/koraku-api/`** (`koraku-backend-proxy.ts`, `koraku-api-routes.ts`) so auth cookies become upstream Bearer tokens without exposing service keys.

## Project layout

```
koraku-cloud/
├── koraku/                  # SDK sources (synced to meet447/Koraku)
├── koraku_cloud/            # Cloud: Supabase, automations, product routes
├── web/                     # Next.js + BFF (/koraku-api/*)
├── packages/koraku-client/  # TypeScript SSE client
├── docs/
├── scripts/
└── tests/
```

## API endpoints (Cloud)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Public liveness |
| `/health/detail` | GET | Ops snapshot (`HEALTH_DETAIL_TOKEN`) |
| `/stream` | POST | SSE chat |
| `/runs` | POST | Start detached run |
| `/api/automations` | CRUD | Scheduled / event automations |
| `/api/personalization` | GET/PUT | Memory / soul per org |
| `/api/admin/*` | … | Platform admin (credits, orgs) — operators only |
| `/api/composio/*` | … | Connected apps |
| `/sendblue/webhook` | POST | iMessage inbound |

Browser clients use **`/koraku-api/...`** on the Next.js host. See [docs/DATA_LIFECYCLE.md](docs/DATA_LIFECYCLE.md).

### Platform admin (`/admin`)

Operators manage org credits, limits, and suspensions at **`/admin`** (Dashboard, Organizations). Grant access by setting **`PLATFORM_ADMIN_USER_IDS`** on the Python API (comma-separated Supabase user UUIDs) or inserting a row into **`koraku_platform_admin`**. All mutations are written to **`koraku_admin_audit_log`**.

## Configuration

See [`.env.example`](.env.example). Production checklist: [docs/SELF_HOST.md#production-checklist](docs/SELF_HOST.md#production-checklist).

## Embed the SDK (without this web app)

Install from [Koraku](https://github.com/meet447/Koraku) or develop in-process from `koraku/` here. See [docs/SDK.md](docs/SDK.md).

## License

[MIT](LICENSE) © 2026 Meet Sonawane and Koraku contributors.
