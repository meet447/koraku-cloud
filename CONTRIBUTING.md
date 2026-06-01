# Contributing to Koraku

Thanks for your interest in making Koraku better. Koraku is a personal AI
buddy / second brain — issues, bug reports, ideas, and pull requests are all
welcome.

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). By
participating you agree to uphold it. Report unacceptable behavior to
**meet.sonawane2015@gmail.com**.

## Ways to contribute

- **Bug reports** — open an issue with steps to reproduce, expected vs. actual
  behavior, and your environment (OS, Python version, LLM provider).
- **Feature ideas** — open an issue first to discuss scope before writing code,
  especially for anything that touches the agent loop, tool registry, or
  storage schema.
- **Documentation** — README, `docs/`, and inline help strings are all fair
  game.
- **Tools and integrations** — adding a new tool to `koraku/tools/` or a new
  Composio toolkit binding is one of the easiest ways to start.
- **Web UI** — Next.js work lives in `web/`.

## Development setup

```bash
# Python backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in at least one LLM provider key

# Run the API
python main.py
```

```bash
# Next.js web app (separate terminal)
cd web
npm install
npm run dev
```

For full configuration (Supabase auth, Composio, Blaxel cloud sandboxes),
see [`README.md`](README.md) and [`.env.example`](.env.example).

## Running tests

```bash
# Structure + smoke (no API key needed)
pytest tests/test_structure.py -q

# Full suite
pytest -q
```

Add tests under `tests/` mirroring the `koraku/` package layout. Tests that hit
external services (Supabase, Composio, LLM providers) should be guarded by an
env var check or marked so they can be skipped in CI by default.

## Pull request checklist

Before opening a PR:

1. **Run `pytest -q`** — keep the suite green.
2. **Run the app locally** for any change that touches the chat loop, tools,
   or the web UI. Don't ship UI changes you haven't actually clicked through.
3. **Write a focused commit message.** One sentence describing the *why*,
   plus details if the change is non-obvious. Don't add co-author trailers
   you didn't agree on with the human author.
4. **Update docs.** If you add an env var, document it in `.env.example`. If
   you change a public API or SSE event shape, update the README.
5. **One logical change per PR.** Refactors and unrelated cleanups belong in
   their own PR.

## Coding conventions

- **Python:** type hints on public functions, `from __future__ import
  annotations` at the top of new modules, async-first for IO. Keep modules
  small and cohesive — `koraku/` is laid out by domain (`agent/`, `tools/`,
  `integrations/`, ...).
- **TypeScript / Next.js:** strict mode, server components by default, client
  components only when you need state or browser APIs. Tailwind for styling.
- **No secrets in code.** Anything sensitive goes through `.env` /
  `web/.env.local`. Server-only keys (Supabase service role, LLM provider keys)
  must never appear with a `NEXT_PUBLIC_` prefix.
- **Be careful with the agent loop.** It is the hot path. New tools should
  fail closed (return an error string the model can read), not raise.

## Filing security issues

Please do **not** file security vulnerabilities as public issues. See
[`SECURITY.md`](SECURITY.md) for the private disclosure process.

## License

By contributing, you agree that your contributions will be licensed under the
[MIT License](LICENSE) that covers the project.
