-- Finish org tenancy: backfill null org_id, enforce NOT NULL, tighten RLS.

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

alter table public.chat_thread alter column org_id set not null;
alter table public.koraku_automation alter column org_id set not null;
alter table public.koraku_automation_run alter column org_id set not null;
alter table public.koraku_personalization alter column org_id set not null;

create index if not exists koraku_automation_run_org_started_idx
  on public.koraku_automation_run (org_id, started_at desc);

-- chat_thread: require org membership (no null org_id escape hatch)

drop policy if exists "chat_thread_select_own" on public.chat_thread;
drop policy if exists "chat_thread_delete_own" on public.chat_thread;

create policy "chat_thread_select_own"
  on public.chat_thread for select
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
    and exists (
      select 1 from public.koraku_org_member m
      where m.org_id = chat_thread.org_id and m.user_id = auth.uid()
    )
  );

-- chat_message: org-aware via thread

drop policy if exists "chat_message_select_own_thread" on public.chat_message;
drop policy if exists "chat_message_insert_own_thread" on public.chat_message;
drop policy if exists "chat_message_update_own_thread" on public.chat_message;
drop policy if exists "chat_message_delete_own_thread" on public.chat_message;

create policy "chat_message_select_own_thread"
  on public.chat_message for select
  using (
    exists (
      select 1 from public.chat_thread t
      join public.koraku_org_member m on m.org_id = t.org_id and m.user_id = auth.uid()
      where t.id = chat_message.thread_id and t.user_id = auth.uid()
    )
  );

create policy "chat_message_insert_own_thread"
  on public.chat_message for insert
  with check (
    exists (
      select 1 from public.chat_thread t
      join public.koraku_org_member m on m.org_id = t.org_id and m.user_id = auth.uid()
      where t.id = chat_message.thread_id and t.user_id = auth.uid()
    )
  );

create policy "chat_message_update_own_thread"
  on public.chat_message for update
  using (
    exists (
      select 1 from public.chat_thread t
      join public.koraku_org_member m on m.org_id = t.org_id and m.user_id = auth.uid()
      where t.id = chat_message.thread_id and t.user_id = auth.uid()
    )
  );

create policy "chat_message_delete_own_thread"
  on public.chat_message for delete
  using (
    exists (
      select 1 from public.chat_thread t
      join public.koraku_org_member m on m.org_id = t.org_id and m.user_id = auth.uid()
      where t.id = chat_message.thread_id and t.user_id = auth.uid()
    )
  );

-- automations: org-scoped (no null org_id escape hatch)

drop policy if exists "koraku_automation_select_own" on public.koraku_automation;
drop policy if exists "koraku_automation_delete_own" on public.koraku_automation;

create policy "koraku_automation_select_own"
  on public.koraku_automation for select
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
    and exists (
      select 1 from public.koraku_org_member m
      where m.org_id = koraku_automation.org_id and m.user_id = auth.uid()
    )
  );

-- automation runs: org-scoped

drop policy if exists "koraku_automation_run_select_own" on public.koraku_automation_run;
drop policy if exists "koraku_automation_run_insert_own" on public.koraku_automation_run;
drop policy if exists "koraku_automation_run_update_own" on public.koraku_automation_run;
drop policy if exists "koraku_automation_run_delete_own" on public.koraku_automation_run;

create policy "koraku_automation_run_select_own"
  on public.koraku_automation_run for select
  using (
    auth.uid() = user_id
    and exists (
      select 1 from public.koraku_org_member m
      where m.org_id = koraku_automation_run.org_id and m.user_id = auth.uid()
    )
  );

create policy "koraku_automation_run_insert_own"
  on public.koraku_automation_run for insert
  with check (
    auth.uid() = user_id
    and org_id is not null
    and exists (
      select 1 from public.koraku_org_member m
      where m.org_id = koraku_automation_run.org_id and m.user_id = auth.uid()
    )
  );

create policy "koraku_automation_run_update_own"
  on public.koraku_automation_run for update
  using (
    auth.uid() = user_id
    and exists (
      select 1 from public.koraku_org_member m
      where m.org_id = koraku_automation_run.org_id and m.user_id = auth.uid()
    )
  );

create policy "koraku_automation_run_delete_own"
  on public.koraku_automation_run for delete
  using (
    auth.uid() = user_id
    and exists (
      select 1 from public.koraku_org_member m
      where m.org_id = koraku_automation_run.org_id and m.user_id = auth.uid()
    )
  );

-- personalization: org-scoped (no null org_id escape hatch)

drop policy if exists "koraku_personalization_select_own" on public.koraku_personalization;
drop policy if exists "koraku_personalization_delete_own" on public.koraku_personalization;

create policy "koraku_personalization_select_own"
  on public.koraku_personalization for select
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
    and exists (
      select 1 from public.koraku_org_member m
      where m.org_id = koraku_personalization.org_id and m.user_id = auth.uid()
    )
  );
