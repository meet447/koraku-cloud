-- Composio-backed event triggers (Gmail, Slack, etc.) alongside generic webhooks.

alter table public.koraku_automation
  add column if not exists event_source text not null default 'generic'
    check (event_source in ('generic', 'composio')),
  add column if not exists composio_trigger_slug text,
  add column if not exists composio_trigger_id text;

create index if not exists koraku_automation_composio_trigger_idx
  on public.koraku_automation (composio_trigger_id)
  where composio_trigger_id is not null and status = 'active';
