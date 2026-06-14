# Contributing to Koraku

Thanks for helping improve Koraku — an AI workspace in the cloud (connected apps, agents with approval gates, automations, and optional iMessage). This repository is the **product monorepo** (web UI, `koraku_cloud`, Supabase). The open-source SDK is developed here under `koraku/` and synced to [meet447/Koraku](https://github.com/meet447/Koraku).

Product context: [README.md](README.md) · [docs/OVERVIEW.md](docs/OVERVIEW.md)

## Code of Conduct

[Contributor Covenant](CODE_OF_CONDUCT.md) — report issues to **meet.sonawane2015@gmail.com**.

## Where to contribute

| Change | Repo |
|--------|------|
| Agent core, tools, `Koraku` API, `@koraku/client` | PR here **and** export to Koraku (see below) or PR on [Koraku](https://github.com/meet447/Koraku) |
| Automations UI, Supabase schema, `koraku_cloud` routes | **koraku-cloud** only |
| Next.js app | `web/` in this repo |

## Development setup

```bash
git clone https://github.com/meet447/koraku-cloud.git
cd koraku-cloud
./scripts/install-monorepo.sh
cp .env.example .env
./scripts/run-api.sh
```

```bash
cd web && npm install && npm run dev
```

See [README.md](README.md), [docs/OVERVIEW.md](docs/OVERVIEW.md), [docs/SELF_HOST.md](docs/SELF_HOST.md), and [`.env.example`](.env.example).

## Sync SDK to the open-source repo

```bash
git clone https://github.com/meet447/Koraku.git ../Koraku
./scripts/export-sdk-oss-repo.sh ../Koraku
cd ../Koraku && pytest -q
```

## Tests

```bash
pytest -q
./scripts/verify-sdk-wheel.sh
python3 scripts/check_cloud_imports.py
```

Cloud-only tests live under `tests/automations/` and similar; they are excluded from the Koraku export.

## Pull requests

1. Run `pytest -q` (and wheel check if you changed packaging).
2. Document new env vars in `.env.example`.
3. One logical change per PR.
4. No secrets in code; no `Co-authored-by` trailers unless agreed with the author.

## Security

See [SECURITY.md](SECURITY.md) — do not file vulnerabilities as public issues.

## License

Contributions are licensed under the project [MIT License](LICENSE).
