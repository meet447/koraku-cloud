# Koraku Cloud

> Koraku product monorepo — web app, Supabase-backed chat, automations, and the `koraku_cloud` API layer.

The **open-source embeddable SDK** (`koraku`, `@koraku/client`) is maintained separately: [github.com/meet447/Koraku](https://github.com/meet447/Koraku). This repo vendors the same `koraku/` sources for Cloud development and syncs them to Koraku via `./scripts/export-sdk-oss-repo.sh`.

- **Repo:** [github.com/meet447/koraku-cloud](https://github.com/meet447/koraku-cloud)
- **License:** [MIT](LICENSE)
- **Security:** [SECURITY.md](SECURITY.md) · **Conduct:** [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- **Contributing:** [CONTRIBUTING.md](CONTRIBUTING.md)

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/SELF_HOST.md](docs/SELF_HOST.md) | Install (Docker / manual), env, production checklist |
| [docs/SDK.md](docs/SDK.md) | Embed Koraku in Python or TypeScript (export source for Koraku repo) |
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

## What Koraku Cloud includes

- **AI buddy** — streaming chat with tools (web, files, shell, connected apps).
- **Second brain** — `Memory.md` / `Soul.md` plus optional Supabase personalization per organization.
- **Automations** — cron-style jobs and Composio event triggers, with run history.
- **Connected apps** — Gmail, Calendar, Slack, and more via [Composio](https://composio.dev/).
- **iMessage (optional)** — inbound/outbound via [SendBlue](docs/SENDBLUE.md).

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
| `/api/composio/*` | … | Connected apps |
| `/sendblue/webhook` | POST | iMessage inbound |

Browser clients use **`/koraku-api/...`** on the Next.js host. See [docs/DATA_LIFECYCLE.md](docs/DATA_LIFECYCLE.md).

## Configuration

See [`.env.example`](.env.example). Production checklist: [docs/SELF_HOST.md#production-checklist](docs/SELF_HOST.md#production-checklist).

## Embed the SDK (without this web app)

Install from [Koraku](https://github.com/meet447/Koraku) or develop in-process from `koraku/` here. See [docs/SDK.md](docs/SDK.md).

## License

[MIT](LICENSE) © 2026 Meet Sonawane and Koraku contributors.
