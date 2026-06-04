# Scripts

| Script | Purpose |
|--------|---------|
| `install-monorepo.sh` | Create **only** `koraku-cloud/.venv` and editable-install SDK + cloud |
| `run-api.sh` | Start API via **uvicorn** (no global `koraku-server` command) |
| `cleanup-extra-venvs.sh` | Delete stray `venv/` dirs (e.g. sibling `koraku/.venv`) |
| `install-web.sh` | Next.js deps in `web/` |
| `verify-sdk-wheel.sh` | Assert PyPI wheel excludes `koraku_cloud` |
| `check_cloud_imports.py` | Guard: no eager `koraku_cloud` imports in `koraku/` |
| `ngrok-sendblue.sh` | Tunnel for SendBlue webhooks (dev) |

## Run the API

```bash
./scripts/install-monorepo.sh
source .venv/bin/activate
./scripts/run-api.sh
```

Cloud (default): `koraku_cloud.app:app`  
SDK only: `KORAKU_PROFILE=sdk ./scripts/run-api.sh`
