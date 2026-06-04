# Packaging: SDK vs Cloud

## Layout

```
koraku-cloud/          # this repo (monorepo)
├── koraku/            # public SDK (agent, tools, server_sdk)
├── koraku_cloud/      # Cloud product (Supabase, automations, web APIs)
├── web/               # Next.js app
├── packages/koraku-client/
├── docs/
├── scripts/
└── tests/
```

## PyPI (`koraku`)

The published wheel includes **`koraku` only** — not `koraku_cloud`.

| Install | Use case |
|---------|----------|
| `pip install koraku` | Embed agents, local tools, filesystem memory |
| `pip install "koraku[server]"` | Self-hosted `/health` + `/stream` (run with uvicorn) |
| `pip install "koraku[all]"` | Server + Composio + Blaxel + Supermemory |

Default: `KORAKU_PROFILE=sdk`.

## Monorepo / Cloud

```bash
./scripts/install-monorepo.sh
export KORAKU_PROFILE=cloud
./scripts/run-api.sh
# or: uvicorn koraku_cloud.app:app --reload
```

| Variable | SDK | Cloud |
|----------|-----|-------|
| `KORAKU_PROFILE` | `sdk` | `cloud` |
| `KORAKU_SERVER_APP` | `sdk` | `cloud` |
| `SUPABASE_URL` + service role | optional | required |

## Server entrypoints

| App | Module |
|-----|--------|
| SDK | `koraku.server_sdk:app` |
| Cloud | `koraku_cloud.app:app` |

`koraku.server:create_app()` picks SDK vs Cloud from profile / `KORAKU_SERVER_APP`.

## Guards

```bash
./scripts/verify-sdk-wheel.sh
python3 scripts/check_cloud_imports.py
```

## Future repo split

| Repo | Contents |
|------|----------|
| **koraku-sdk** (public) | `koraku/`, `packages/koraku-client`, `examples/`, SDK docs |
| **koraku-cloud** (private) | `koraku_cloud/`, `web/`, Dockerfile, product docs |

After PyPI publish: `pip install "koraku[server,all]"` then `pip install "koraku-cloud[pypi]"`.

Until then: `./scripts/install-monorepo.sh`.

Keep `version` in root `pyproject.toml` and `koraku_cloud/pyproject.toml` aligned.
