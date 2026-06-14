# Koraku

> Embeddable ReAct agent SDK — your personal AI buddy, open source.

**Koraku** is a Python SDK for building agents with tools (web, files, shell, Composio integrations) and an optional self-hosted HTTP server. Use it in-process, behind FastAPI, or from web clients via [`@koraku/client`](packages/koraku-client/).

The full **Koraku** product (Next.js app, Supabase, automations, workspace APIs) lives in the public monorepo: [github.com/meet447/koraku-cloud](https://github.com/meet447/koraku-cloud).

- **License:** [MIT](LICENSE)
- **Docs:** [docs/SDK.md](docs/SDK.md)
- **Security:** [SECURITY.md](SECURITY.md)

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,server,all]"
```

```python
from koraku import Koraku, KorakuConfig

agent = Koraku(KorakuConfig(fireworks_api_key="...", llm_provider="fireworks"))
async for event in agent.stream("Summarize this repo"):
    print(event)
```

## Self-hosted API (SDK server)

```bash
cp .env.example .env   # add LLM keys
uvicorn koraku.server_sdk:app --reload --port 8000
```

- `GET /health` — liveness
- `POST /stream` — chat SSE
- `GET /api/composio/*` — Connections proxy (when `COMPOSIO_API_KEY` is set)

## Install options

| Extra | Purpose |
|-------|---------|
| `koraku` | Core SDK |
| `koraku[server]` | FastAPI + uvicorn |
| `koraku[composio]` | Gmail, Slack, Drive, … via Composio |
| `koraku[blaxel]` | Cloud sandboxes |
| `koraku[all]` | Common self-host bundle |

## Development

```bash
pip install -e ".[dev,all]"
pytest -q
./scripts/verify-sdk-wheel.sh
```

## Related repos

| Repo | What |
|------|------|
| **Koraku** (this repo) | Open-source `koraku` Python SDK + `@koraku/client` |
| [koraku-cloud](https://github.com/meet447/koraku-cloud) | Product server, web UI, automations |
