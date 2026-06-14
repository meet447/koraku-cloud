# Koraku overview

Product context for contributors and operators. For install steps see [SELF_HOST.md](SELF_HOST.md); for embedding the agent see [SDK.md](SDK.md).

## What Koraku is

Koraku is an **AI workspace in the cloud**. Users connect apps they already use (Gmail, Notion, Linear, Calendar, and dozens more), describe outcomes in plain language, and agents pull live context, draft results in a cloud workspace, and ask before high-impact actions.

This repo (**koraku-cloud**) ships the full product: Next.js web app, Supabase persistence, automations, and the `koraku_cloud` API. The embeddable SDK (`koraku`, `@koraku/client`) is published from [meet447/Koraku](https://github.com/meet447/Koraku).

## Goals

| Goal | How Koraku helps |
|------|------------------|
| One place for agent work | Hosted chat, workspace files, automations, and run history |
| Connected stack | OAuth to 35+ apps; context stays in Koraku across sessions |
| Natural language, not scripts | Outcomes in plain language; personalization and memory on every run |
| User control | Approval gates before sensitive actions; revoke integrations anytime |
| Pick up anywhere | Web app, scheduled automations, optional iMessage / SMS |

## How it works

1. **Connect** — Link apps once in Settings (Composio OAuth).
2. **Instruct** — Describe what you want in chat or automation instructions.
3. **Review & run** — Drafts land in the workspace; Koraku asks before sending or changing external systems.

## Memory and context (product)

Three layers work together; see [DATA_LIFECYCLE.md](DATA_LIFECYCLE.md) for storage detail.

| Layer | What users edit | Where it lives |
|-------|-----------------|----------------|
| **Personalization** | Agent name, standing preferences (`memory`), persona (`soul`) | Supabase `koraku_personalization` per `(user_id, org_id)` |
| **Learned memory** | Facts inferred from conversations (read-only in UI) | [Supermemory](https://supermemory.ai/) when `SUPERMEMORY_API_KEY` is set |
| **Agent skills** | Custom SKILL.md instructions per org | Supabase `koraku_skill` + bundled defaults in the API image |

Chat history and workspace files are separate: threads/messages in Supabase; agent-created files in the cloud workspace (Blaxel or server execution).

## Repositories

| Repo | Role |
|------|------|
| [koraku-cloud](https://github.com/meet447/koraku-cloud) | Product monorepo (this repo) |
| [Koraku](https://github.com/meet447/Koraku) | Open-source SDK on PyPI / npm |

Sync SDK changes: `./scripts/export-sdk-oss-repo.sh` — see [PACKAGING.md](PACKAGING.md).

## Related docs

| Doc | Purpose |
|-----|---------|
| [SELF_HOST.md](SELF_HOST.md) | Docker, manual install, production checklist |
| [SDK.md](SDK.md) | Embed Koraku without the web app |
| [DATA_LIFECYCLE.md](DATA_LIFECYCLE.md) | Stores, retention, export/delete |
| [SENDBLUE.md](SENDBLUE.md) | iMessage / SMS |
