-- Koraku saved automations + run history (replaces SQLite under .koraku/).
-- Requires authenticated users (Supabase Auth JWT) for browser/Next access;
-- the Python backend uses the service role and sets user_id explicitly.

create table if not exists public.koraku_automation (
  id text primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  title text not null,
  headline text not null default '',
  natural_language_spec text not null,
  trigger_mode text not null check (trigger_mode in ('scheduled', 'event')),
  status text not null default 'active' check (status in ('active', 'paused')),
  timezone text,
  cron_expression text,
  event_display text,
  toolkits jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  last_run_at timestamptz,
  next_run_at timestamptz
);

create index if not exists koraku_automation_user_updated_idx
  on public.koraku_automation (user_id, updated_at desc);

create index if not exists koraku_automation_scheduled_active_idx
  on public.koraku_automation (trigger_mode, status)
  where trigger_mode = 'scheduled' and status = 'active';

create table if not exists public.koraku_automation_run (
  id text primary key,
  automation_id text not null references public.koraku_automation (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  status text not null,
  trigger_summary text not null default '',
  result_summary text,
  error text,
  started_at timestamptz not null,
  finished_at timestamptz,
  duration_ms integer
);

create index if not exists koraku_automation_run_auto_started_idx
  on public.koraku_automation_run (automation_id, started_at desc);

alter table public.koraku_automation enable row level security;
alter table public.koraku_automation_run enable row level security;

drop policy if exists "koraku_automation_select_own" on public.koraku_automation;
drop policy if exists "koraku_automation_insert_own" on public.koraku_automation;
drop policy if exists "koraku_automation_update_own" on public.koraku_automation;
drop policy if exists "koraku_automation_delete_own" on public.koraku_automation;

drop policy if exists "koraku_automation_run_select_own" on public.koraku_automation_run;
drop policy if exists "koraku_automation_run_insert_own" on public.koraku_automation_run;
drop policy if exists "koraku_automation_run_update_own" on public.koraku_automation_run;
drop policy if exists "koraku_automation_run_delete_own" on public.koraku_automation_run;

create policy "koraku_automation_select_own"
  on public.koraku_automation for select
  using (auth.uid() = user_id);

create policy "koraku_automation_insert_own"
  on public.koraku_automation for insert
  with check (auth.uid() = user_id);

create policy "koraku_automation_update_own"
  on public.koraku_automation for update
  using (auth.uid() = user_id);

create policy "koraku_automation_delete_own"
  on public.koraku_automation for delete
  using (auth.uid() = user_id);

create policy "koraku_automation_run_select_own"
  on public.koraku_automation_run for select
  using (auth.uid() = user_id);

create policy "koraku_automation_run_insert_own"
  on public.koraku_automation_run for insert
  with check (auth.uid() = user_id);

create policy "koraku_automation_run_update_own"
  on public.koraku_automation_run for update
  using (auth.uid() = user_id);

create policy "koraku_automation_run_delete_own"
  on public.koraku_automation_run for delete
  using (auth.uid() = user_id);

grant select, insert, update, delete on public.koraku_automation to authenticated;
grant select, insert, update, delete on public.koraku_automation_run to authenticated;
