-- Koraku chat tables + RLS (run via Supabase SQL editor or `supabase db push`).
-- Requires authenticated users (Supabase Auth JWT).

create table if not exists public.chat_thread (
  id text primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  title text not null default 'New chat',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists chat_thread_user_id_updated_at_idx
  on public.chat_thread (user_id, updated_at desc);

create table if not exists public.chat_message (
  id text primary key,
  thread_id text not null references public.chat_thread (id) on delete cascade,
  role text not null,
  content_json jsonb not null,
  created_at timestamptz not null default now()
);

create index if not exists chat_message_thread_id_created_at_idx
  on public.chat_message (thread_id, created_at);

alter table public.chat_thread enable row level security;
alter table public.chat_message enable row level security;

drop policy if exists "chat_thread_select_own" on public.chat_thread;
drop policy if exists "chat_thread_insert_own" on public.chat_thread;
drop policy if exists "chat_thread_update_own" on public.chat_thread;
drop policy if exists "chat_thread_delete_own" on public.chat_thread;
drop policy if exists "chat_message_select_own_thread" on public.chat_message;
drop policy if exists "chat_message_insert_own_thread" on public.chat_message;
drop policy if exists "chat_message_update_own_thread" on public.chat_message;
drop policy if exists "chat_message_delete_own_thread" on public.chat_message;

create policy "chat_thread_select_own"
  on public.chat_thread for select
  using (auth.uid() = user_id);

create policy "chat_thread_insert_own"
  on public.chat_thread for insert
  with check (auth.uid() = user_id);

create policy "chat_thread_update_own"
  on public.chat_thread for update
  using (auth.uid() = user_id);

create policy "chat_thread_delete_own"
  on public.chat_thread for delete
  using (auth.uid() = user_id);

create policy "chat_message_select_own_thread"
  on public.chat_message for select
  using (
    exists (
      select 1 from public.chat_thread t
      where t.id = chat_message.thread_id and t.user_id = auth.uid()
    )
  );

create policy "chat_message_insert_own_thread"
  on public.chat_message for insert
  with check (
    exists (
      select 1 from public.chat_thread t
      where t.id = chat_message.thread_id and t.user_id = auth.uid()
    )
  );

create policy "chat_message_update_own_thread"
  on public.chat_message for update
  using (
    exists (
      select 1 from public.chat_thread t
      where t.id = chat_message.thread_id and t.user_id = auth.uid()
    )
  );

create policy "chat_message_delete_own_thread"
  on public.chat_message for delete
  using (
    exists (
      select 1 from public.chat_thread t
      where t.id = chat_message.thread_id and t.user_id = auth.uid()
    )
  );

grant select, insert, update, delete on public.chat_thread to authenticated;
grant select, insert, update, delete on public.chat_message to authenticated;
