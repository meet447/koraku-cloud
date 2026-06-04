# Packaging: SDK vs Cloud

## Repositories

| Repo | Contents |
|------|----------|
| [meet447/Koraku](https://github.com/meet447/Koraku) | Open-source `koraku` Python SDK, `@koraku/client`, examples, SDK tests |
| **koraku-cloud** (this repo) | `koraku_cloud/`, `web/`, product docs, Docker, Cloud CI |

Sync SDK sources to Koraku with:

```bash
./scripts/export-sdk-oss-repo.sh /path/to/Koraku-clone
```

## Layout (monorepo)

```
koraku-cloud/
├── koraku/            # SDK sources (also published from Koraku repo)
├── koraku_cloud/      # Cloud product (Supabase, automations, web APIs)
├── web/               # Next.js app
├── packages/koraku-client/
├── scripts/oss-repo/  # Overlay files applied on export
└── tests/
```

## PyPI (`koraku`)

Build and publish wheels from the **Koraku** repo (or verify here before export):

```bash
./scripts/verify-sdk-wheel.sh
```

The wheel includes **`koraku` only** — not `koraku_cloud`.

| Install | Use case |
|---------|----------|
| `pip install koraku` | Embed agents, local tools, filesystem memory |
| `pip install "koraku[server]"` | Self-hosted `/health` + `/stream` |
| `pip install "koraku[all]"` | Server + Composio + Blaxel + Supermemory |

## Monorepo / Cloud

```bash
./scripts/install-monorepo.sh
./scripts/run-api.sh                    # default: koraku_cloud.app:app
KORAKU_SERVER_APP=sdk ./scripts/run-api.sh   # SDK-only server
```

| Variable | SDK server | Cloud server |
|----------|------------|--------------|
| `KORAKU_SERVER_APP` | `sdk` | `cloud` (default) |
| `SUPABASE_URL` + service role | optional | required for product features |

## Server entrypoints

| App | Module |
|-----|--------|
| SDK | `koraku.server_sdk:app` |
| Cloud | `koraku_cloud.app:app` |
| Either | `koraku.server:app` (uses `KORAKU_SERVER_APP`) |

## SDK / Cloud boundary

Product behavior is registered via `koraku.core.product_hooks` when `bootstrap_cloud()` runs.
See [MIGRATION_SDK_CLOUD.md](./MIGRATION_SDK_CLOUD.md) for the phased split plan.

## Guards

```bash
./scripts/verify-sdk-wheel.sh
python3 scripts/check_cloud_imports.py
```

Keep `version` in root `pyproject.toml` and `koraku_cloud/pyproject.toml` aligned when cutting releases.
