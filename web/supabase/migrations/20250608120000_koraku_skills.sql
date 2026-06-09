-- Org-scoped agent skills (replaces workspace ``.koraku/skills/`` for Koraku Cloud).

create table if not exists public.koraku_skill (
  org_id uuid not null references public.koraku_organization (id) on delete cascade,
  slug text not null check (slug ~ '^[a-z0-9][a-z0-9-]{0,63}$'),
  name text not null default '',
  description text not null default '',
  body text not null default '',
  enabled boolean not null default true,
  updated_at timestamptz not null default now(),
  primary key (org_id, slug)
);

create index if not exists koraku_skill_org_enabled_idx
  on public.koraku_skill (org_id, enabled, updated_at desc);

alter table public.koraku_skill enable row level security;

drop policy if exists "koraku_skill_select_org_member" on public.koraku_skill;
drop policy if exists "koraku_skill_insert_org_member" on public.koraku_skill;
drop policy if exists "koraku_skill_update_org_member" on public.koraku_skill;
drop policy if exists "koraku_skill_delete_org_member" on public.koraku_skill;

create policy "koraku_skill_select_org_member"
  on public.koraku_skill for select
  using (
    exists (
      select 1 from public.koraku_org_member m
      where m.org_id = koraku_skill.org_id and m.user_id = auth.uid()
    )
  );

create policy "koraku_skill_insert_org_member"
  on public.koraku_skill for insert
  with check (
    exists (
      select 1 from public.koraku_org_member m
      where m.org_id = koraku_skill.org_id and m.user_id = auth.uid()
    )
  );

create policy "koraku_skill_update_org_member"
  on public.koraku_skill for update
  using (
    exists (
      select 1 from public.koraku_org_member m
      where m.org_id = koraku_skill.org_id and m.user_id = auth.uid()
    )
  );

create policy "koraku_skill_delete_org_member"
  on public.koraku_skill for delete
  using (
    exists (
      select 1 from public.koraku_org_member m
      where m.org_id = koraku_skill.org_id and m.user_id = auth.uid()
    )
  );

grant select, insert, update, delete on public.koraku_skill to authenticated;
