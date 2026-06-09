-- Admin org search: email (auth.users), org UUID, or org name.

create or replace function public.koraku_admin_search_orgs(
  p_query text,
  p_limit int default 25
)
returns table (
  id uuid,
  name text,
  kind text,
  created_at timestamptz,
  matched_user_id uuid,
  matched_email text,
  member_role text
)
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  vq text := trim(p_query);
  vlim int := greatest(1, least(coalesce(p_limit, 25), 50));
begin
  if vq is null or vq = '' then
    return;
  end if;

  if position('@' in vq) > 0 then
    return query
    select
      o.id,
      o.name,
      o.kind,
      o.created_at,
      u.id,
      u.email::text,
      m.role
    from auth.users u
    join public.koraku_org_member m on m.user_id = u.id
    join public.koraku_organization o on o.id = m.org_id
    where u.email ilike '%' || vq || '%'
    order by m.is_default desc, o.created_at desc
    limit vlim;
    return;
  end if;

  if vq ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' then
    return query
    select o.id, o.name, o.kind, o.created_at, null::uuid, null::text, null::text
    from public.koraku_organization o
    where o.id = vq::uuid
    limit vlim;
    return;
  end if;

  return query
  select o.id, o.name, o.kind, o.created_at, null::uuid, null::text, null::text
  from public.koraku_organization o
  where o.name ilike '%' || vq || '%'
  order by o.created_at desc
  limit vlim;
end;
$$;

grant execute on function public.koraku_admin_search_orgs(text, int) to service_role;
