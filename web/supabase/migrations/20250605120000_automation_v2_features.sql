-- Scheduling presets, run progress, skip/failure policy, fingerprints, webhook events.

alter table public.koraku_automation
  add column if not exists schedule_preset jsonb,
  add column if not exists consecutive_failures integer not null default 0,
  add column if not exists max_failures_before_pause integer not null default 3,
  add column if not exists current_run_id text,
  add column if not exists last_success_fingerprint text,
  add column if not exists event_webhook_token_hash text;

alter table public.koraku_automation_run
  add column if not exists progress_phase text,
  add column if not exists progress_detail text,
  add column if not exists result_fingerprint text,
  add column if not exists outcome_label text;

create index if not exists koraku_automation_run_running_idx
  on public.koraku_automation_run (automation_id, started_at desc)
  where status = 'running';
