-- Multi-tenant organizations (Koraku Cloud). Each user gets a personal org on first use.
-- Service role + RPC ``koraku_ensure_personal_org`` are used by the Python API; RLS uses membership.

create table if not exists public.koraku_organization (
  id uuid primary key default gen_random_uuid(),
  name text not null default 'Personal',
  kind text not null default 'personal' check (kind in ('personal', 'team')),
  created_at timestamptz not null default now()
);

create table if not exists public.koraku_org_member (
  org_id uuid not null references public.koraku_organization (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  role text not null default 'owner' check (role in ('owner', 'admin', 'member')),
  is_default boolean not null default false,
  created_at timestamptz not null default now(),
  primary key (org_id, user_id)
);

create unique index if not exists koraku_org_member_one_default_per_user_idx
  on public.koraku_org_member (user_id)
  where is_default;

create index if not exists koraku_org_member_user_id_idx
  on public.koraku_org_member (user_id);

-- Tenant column on existing product tables (nullable → backfill → NOT NULL).

alter table public.chat_thread
  add column if not exists org_id uuid references public.koraku_organization (id) on delete cascade;

alter table public.koraku_automation
  add column if not exists org_id uuid references public.koraku_organization (id) on delete cascade;

alter table public.koraku_automation_run
  add column if not exists org_id uuid references public.koraku_organization (id) on delete cascade;

alter table public.koraku_personalization
  add column if not exists org_id uuid references public.koraku_organization (id) on delete cascade;

create index if not exists chat_thread_org_id_updated_at_idx
  on public.chat_thread (org_id, updated_at desc);

create index if not exists koraku_automation_org_updated_idx
  on public.koraku_automation (org_id, updated_at desc);

-- Ensure every distinct user with data has a personal org, then set org_id on rows.

create or replace function public.koraku_ensure_personal_org(p_user_id uuid)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_org_id uuid;
begin
  if p_user_id is null then
    raise exception 'user_id required';
  end if;

  select m.org_id into v_org_id
  from public.koraku_org_member m
  where m.user_id = p_user_id and m.is_default
  limit 1;

  if v_org_id is not null then
    return v_org_id;
  end if;

  select m.org_id into v_org_id
  from public.koraku_org_member m
  where m.user_id = p_user_id
  limit 1;

  if v_org_id is not null then
    update public.koraku_org_member
    set is_default = true
    where org_id = v_org_id and user_id = p_user_id;
    return v_org_id;
  end if;

  insert into public.koraku_organization (name, kind)
  values ('Personal', 'personal')
  returning id into v_org_id;

  insert into public.koraku_org_member (org_id, user_id, role, is_default)
  values (v_org_id, p_user_id, 'owner', true);

  return v_org_id;
end;
$$;

grant execute on function public.koraku_ensure_personal_org(uuid) to service_role;
grant execute on function public.koraku_ensure_personal_org(uuid) to authenticated;

-- Backfill org_id for existing rows (no-op when tables are empty).

do $$
declare
  r record;
  v_org uuid;
begin
  for r in select distinct user_id from public.chat_thread where org_id is null
  loop
    v_org := public.koraku_ensure_personal_org(r.user_id);
    update public.chat_thread set org_id = v_org where user_id = r.user_id and org_id is null;
  end loop;

  for r in select distinct user_id from public.koraku_automation where org_id is null
  loop
    v_org := public.koraku_ensure_personal_org(r.user_id);
    update public.koraku_automation set org_id = v_org where user_id = r.user_id and org_id is null;
  end loop;

  for r in select distinct user_id from public.koraku_automation_run where org_id is null
  loop
    v_org := public.koraku_ensure_personal_org(r.user_id);
    update public.koraku_automation_run set org_id = v_org where user_id = r.user_id and org_id is null;
  end loop;

  for r in select distinct user_id from public.koraku_personalization where org_id is null
  loop
    v_org := public.koraku_ensure_personal_org(r.user_id);
    update public.koraku_personalization set org_id = v_org where user_id = r.user_id and org_id is null;
  end loop;
end;
$$;

-- RLS: organizations and membership

alter table public.koraku_organization enable row level security;
alter table public.koraku_org_member enable row level security;

drop policy if exists "koraku_organization_select_member" on public.koraku_organization;
drop policy if exists "koraku_org_member_select_own" on public.koraku_org_member;

create policy "koraku_organization_select_member"
  on public.koraku_organization for select
  using (
    exists (
      select 1 from public.koraku_org_member m
      where m.org_id = koraku_organization.id and m.user_id = auth.uid()
    )
  );

create policy "koraku_org_member_select_own"
  on public.koraku_org_member for select
  using (user_id = auth.uid());

grant select on public.koraku_organization to authenticated;
grant select on public.koraku_org_member to authenticated;

-- Extend chat_thread policies to require org membership (org_id must be set on new rows).

drop policy if exists "chat_thread_select_own" on public.chat_thread;
drop policy if exists "chat_thread_insert_own" on public.chat_thread;
drop policy if exists "chat_thread_update_own" on public.chat_thread;
drop policy if exists "chat_thread_delete_own" on public.chat_thread;

create policy "chat_thread_select_own"
  on public.chat_thread for select
  using (
    auth.uid() = user_id
    and (
      org_id is null
      or exists (
        select 1 from public.koraku_org_member m
        where m.org_id = chat_thread.org_id and m.user_id = auth.uid()
      )
    )
  );

create policy "chat_thread_insert_own"
  on public.chat_thread for insert
  with check (
    auth.uid() = user_id
    and org_id is not null
    and exists (
      select 1 from public.koraku_org_member m
      where m.org_id = chat_thread.org_id and m.user_id = auth.uid()
    )
  );

create policy "chat_thread_update_own"
  on public.chat_thread for update
  using (
    auth.uid() = user_id
    and exists (
      select 1 from public.koraku_org_member m
      where m.org_id = chat_thread.org_id and m.user_id = auth.uid()
    )
  );

create policy "chat_thread_delete_own"
  on public.chat_thread for delete
  using (
    auth.uid() = user_id
    and (
      org_id is null
      or exists (
        select 1 from public.koraku_org_member m
        where m.org_id = chat_thread.org_id and m.user_id = auth.uid()
      )
    )
  );

-- Automations: org-scoped membership

drop policy if exists "koraku_automation_select_own" on public.koraku_automation;
drop policy if exists "koraku_automation_insert_own" on public.koraku_automation;
drop policy if exists "koraku_automation_update_own" on public.koraku_automation;
drop policy if exists "koraku_automation_delete_own" on public.koraku_automation;

create policy "koraku_automation_select_own"
  on public.koraku_automation for select
  using (
    auth.uid() = user_id
    and (
      org_id is null
      or exists (
        select 1 from public.koraku_org_member m
        where m.org_id = koraku_automation.org_id and m.user_id = auth.uid()
      )
    )
  );

create policy "koraku_automation_insert_own"
  on public.koraku_automation for insert
  with check (
    auth.uid() = user_id
    and org_id is not null
    and exists (
      select 1 from public.koraku_org_member m
      where m.org_id = koraku_automation.org_id and m.user_id = auth.uid()
    )
  );

create policy "koraku_automation_update_own"
  on public.koraku_automation for update
  using (
    auth.uid() = user_id
    and exists (
      select 1 from public.koraku_org_member m
      where m.org_id = koraku_automation.org_id and m.user_id = auth.uid()
    )
  );

create policy "koraku_automation_delete_own"
  on public.koraku_automation for delete
  using (
    auth.uid() = user_id
    and (
      org_id is null
      or exists (
        select 1 from public.koraku_org_member m
        where m.org_id = koraku_automation.org_id and m.user_id = auth.uid()
      )
    )
  );

-- Personalization

drop policy if exists "koraku_personalization_select_own" on public.koraku_personalization;
drop policy if exists "koraku_personalization_insert_own" on public.koraku_personalization;
drop policy if exists "koraku_personalization_update_own" on public.koraku_personalization;
drop policy if exists "koraku_personalization_delete_own" on public.koraku_personalization;

create policy "koraku_personalization_select_own"
  on public.koraku_personalization for select
  using (
    auth.uid() = user_id
    and (
      org_id is null
      or exists (
        select 1 from public.koraku_org_member m
        where m.org_id = koraku_personalization.org_id and m.user_id = auth.uid()
      )
    )
  );

create policy "koraku_personalization_insert_own"
  on public.koraku_personalization for insert
  with check (
    auth.uid() = user_id
    and org_id is not null
    and exists (
      select 1 from public.koraku_org_member m
      where m.org_id = koraku_personalization.org_id and m.user_id = auth.uid()
    )
  );

create policy "koraku_personalization_update_own"
  on public.koraku_personalization for update
  using (
    auth.uid() = user_id
    and exists (
      select 1 from public.koraku_org_member m
      where m.org_id = koraku_personalization.org_id and m.user_id = auth.uid()
    )
  );

create policy "koraku_personalization_delete_own"
  on public.koraku_personalization for delete
  using (
    auth.uid() = user_id
    and (
      org_id is null
      or exists (
        select 1 from public.koraku_org_member m
        where m.org_id = koraku_personalization.org_id and m.user_id = auth.uid()
      )
    )
  );
