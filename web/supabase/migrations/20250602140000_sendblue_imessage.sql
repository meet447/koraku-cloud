-- iMessage / SMS via SendBlue: phone linking + dedicated chat thread channel.

alter table public.chat_thread
  add column if not exists channel text not null default 'web'
    check (channel in ('web', 'imessage'));

alter table public.chat_thread
  add column if not exists pinned boolean not null default false;

create index if not exists chat_thread_user_pinned_idx
  on public.chat_thread (user_id, pinned desc, updated_at desc);

create table if not exists public.koraku_phone_link (
  user_id uuid primary key references auth.users (id) on delete cascade,
  org_id uuid not null references public.koraku_organization (id) on delete cascade,
  phone_e164 text not null,
  imessage_thread_id text not null references public.chat_thread (id) on delete cascade,
  verified_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists koraku_phone_link_phone_e164_idx
  on public.koraku_phone_link (phone_e164);

create table if not exists public.koraku_phone_verification (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  phone_e164 text not null,
  code_hash text not null,
  expires_at timestamptz not null,
  created_at timestamptz not null default now()
);

create index if not exists koraku_phone_verification_user_created_idx
  on public.koraku_phone_verification (user_id, created_at desc);

alter table public.koraku_phone_link enable row level security;
alter table public.koraku_phone_verification enable row level security;

drop policy if exists "koraku_phone_link_select_own" on public.koraku_phone_link;
drop policy if exists "koraku_phone_verification_select_own" on public.koraku_phone_verification;

create policy "koraku_phone_link_select_own"
  on public.koraku_phone_link for select
  using (auth.uid() = user_id);

create policy "koraku_phone_verification_select_own"
  on public.koraku_phone_verification for select
  using (auth.uid() = user_id);

grant select on public.koraku_phone_link to authenticated;
grant select on public.koraku_phone_verification to authenticated;
