-- Per-user agent name, Memory, and Soul (replaces repo-local ``.koraku/`` for signed-in users).

create table if not exists public.koraku_personalization (
  user_id uuid primary key references auth.users (id) on delete cascade,
  agent_name text not null default '',
  memory text not null default '',
  soul text not null default '',
  updated_at timestamptz not null default now()
);

create index if not exists koraku_personalization_updated_at_idx
  on public.koraku_personalization (updated_at desc);

alter table public.koraku_personalization enable row level security;

drop policy if exists "koraku_personalization_select_own" on public.koraku_personalization;
drop policy if exists "koraku_personalization_insert_own" on public.koraku_personalization;
drop policy if exists "koraku_personalization_update_own" on public.koraku_personalization;
drop policy if exists "koraku_personalization_delete_own" on public.koraku_personalization;

create policy "koraku_personalization_select_own"
  on public.koraku_personalization for select
  using (auth.uid() = user_id);

create policy "koraku_personalization_insert_own"
  on public.koraku_personalization for insert
  with check (auth.uid() = user_id);

create policy "koraku_personalization_update_own"
  on public.koraku_personalization for update
  using (auth.uid() = user_id);

create policy "koraku_personalization_delete_own"
  on public.koraku_personalization for delete
  using (auth.uid() = user_id);

grant select, insert, update, delete on public.koraku_personalization to authenticated;
