# Security Policy

Thanks for helping keep Koraku and its users safe.

## Supported versions

Koraku is in public beta. Security fixes land on `main`. There is no LTS
branch — please run a recent commit.

## Reporting a vulnerability

**Do not file public GitHub issues for security problems.**

Email **meet.sonawane2015@gmail.com** with:

- A description of the issue and its impact
- Steps to reproduce (PoC code or curl commands are welcome)
- Affected commit hash / version, and your environment
- Whether the issue is already public anywhere

You should get an acknowledgement within **72 hours**. We aim to ship a fix or
mitigation within **14 days** for high-severity issues, longer for lower
severity. We're happy to credit you in the fix commit / release notes once a
fix is out, unless you ask us not to.

## Scope

In scope:

- The Python API in `koraku/` and `main.py`
- The Next.js app in `web/`
- Default deployment configuration (`.env.example`, CORS defaults,
  rate-limit defaults, auth checks)
- Tool sandboxing and the agent's policy layer (`koraku/tools/policy.py`,
  workspace path checks)
- Data flowing through Supabase, Composio, Blaxel, and LLM providers **as
  used by this codebase**

Out of scope (please report to the upstream vendor):

- Vulnerabilities in third-party services themselves (Supabase, Composio,
  Blaxel, LLM providers, Fireworks, Anthropic, OpenAI-compatible endpoints)
- Issues only reachable by an operator who already has the server-only
  service role key, JWT secret, or shell access on the deployment host
- Social-engineering of maintainers

## Hardening notes for operators

If you self-host Koraku, please also read:

- [`docs/PUBLIC_BETA_RUNBOOK.md`](docs/PUBLIC_BETA_RUNBOOK.md) — required env,
  CORS, rate limits, auth checks
- [`docs/DATA_LIFECYCLE.md`](docs/DATA_LIFECYCLE.md) — what data is stored
  where, retention, and export/delete handling

Common mistakes to avoid:

- Setting `CORS_ALLOWED_ORIGINS=*` in production (the server will refuse to
  start)
- Disabling `REQUIRE_AUTH_FOR_CHAT` on a public deployment
- Exposing `SUPABASE_SERVICE_ROLE_KEY` or any LLM provider key to the
  browser via `NEXT_PUBLIC_*`
- Running the API as the filesystem root (`cwd=/`); the server refuses this

## Coordinated disclosure

If you intend to publish a writeup, please coordinate the date with us so a
fix can ship first. We will not threaten or take legal action against
researchers acting in good faith under this policy.
