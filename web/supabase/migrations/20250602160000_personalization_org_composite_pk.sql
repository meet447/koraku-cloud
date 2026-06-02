-- One personalization profile per user per organization (not one global row per user).

do $$
declare
  r record;
  v_org uuid;
begin
  for r in select distinct user_id from public.koraku_personalization where org_id is null
  loop
    v_org := public.koraku_ensure_personal_org(r.user_id);
    update public.koraku_personalization
    set org_id = v_org
    where user_id = r.user_id and org_id is null;
  end loop;
end;
$$;

alter table public.koraku_personalization
  drop constraint if exists koraku_personalization_pkey;

alter table public.koraku_personalization
  add constraint koraku_personalization_pkey primary key (user_id, org_id);

create index if not exists koraku_personalization_org_updated_idx
  on public.koraku_personalization (org_id, updated_at desc);
