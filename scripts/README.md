# Scripts

| Script | Purpose |
|--------|---------|
| `install-monorepo.sh` | Create **only** `koraku-cloud/.venv` and editable-install SDK + cloud |
| `run-api.sh` | Start API via **uvicorn** (`KORAKU_SERVER_APP`, default Cloud) |
| `export-sdk-oss-repo.sh` | Sync SDK tree into a [Koraku](https://github.com/meet447/Koraku) git clone |
| `oss-repo-post-export.py` | OSS-only patches (Composio routes, `pyproject` URLs) |
| `cleanup-extra-venvs.sh` | Delete stray `venv/` dirs (e.g. sibling `koraku/.venv`) |
| `install-web.sh` | Next.js deps in `web/` |
| `verify-sdk-wheel.sh` | Assert PyPI wheel excludes `koraku_cloud` |
| `check_cloud_imports.py` | Guard: no eager `koraku_cloud` imports in `koraku/` |
| `ngrok-sendblue.sh` | Tunnel for SendBlue webhooks (dev) |
| `deploy-vps.sh` | Rsync to VPS and redeploy Docker Compose (see `deploy/vps/`; also used by GitHub Actions) |

## Run the API

```bash
./scripts/install-monorepo.sh
source .venv/bin/activate
./scripts/run-api.sh
```

Cloud (default): `koraku_cloud.app:app`  
SDK only: `KORAKU_SERVER_APP=sdk ./scripts/run-api.sh`

## Publish open-source SDK

```bash
git clone https://github.com/meet447/Koraku.git ../Koraku
./scripts/export-sdk-oss-repo.sh ../Koraku
cd ../Koraku && pytest -q && ./scripts/verify-sdk-wheel.sh
```
