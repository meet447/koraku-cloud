-- Platform admin: audit log, org ops state, credit grants, dashboard stats.

create table if not exists public.koraku_platform_admin (
  user_id uuid primary key references auth.users (id) on delete cascade,
  note text not null default '',
  created_at timestamptz not null default now()
);

alter table public.koraku_platform_admin enable row level security;

-- No policies for authenticated: only service role reads/writes.

create table if not exists public.koraku_admin_audit_log (
  id uuid primary key default gen_random_uuid(),
  actor_user_id uuid not null,
  action text not null,
  target_type text not null check (target_type in ('org', 'user')),
  target_id text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists koraku_admin_audit_log_created_idx
  on public.koraku_admin_audit_log (created_at desc);

alter table public.koraku_admin_audit_log enable row level security;

create table if not exists public.koraku_org_admin_state (
  org_id uuid primary key references public.koraku_organization (id) on delete cascade,
  suspended boolean not null default false,
  suspend_reason text not null default '',
  notes text not null default '',
  updated_at timestamptz not null default now()
);

alter table public.koraku_org_admin_state enable row level security;

-- Grant credits: reduces credits_used (bonus headroom), ledger kind = adjustment.
create or replace function public.koraku_credit_adjust(
  p_org_id uuid,
  p_grant_credits int,
  p_reason text,
  p_actor_user_id uuid,
  p_idempotency_key text
)
returns table (
  settled boolean,
  credits_used bigint,
  credits_limit bigint,
  period_end timestamptz
)
language plpgsql
security definer
set search_path = public
as $$
declare
  v_start date;
  v_period public.koraku_usage_period;
  v_grant int;
begin
  if p_org_id is null or coalesce(trim(p_idempotency_key), '') = '' then
    raise exception 'org_id and idempotency_key required';
  end if;
  v_grant := coalesce(p_grant_credits, 0);
  if v_grant <= 0 then
    raise exception 'grant_credits must be positive';
  end if;

  v_period := public.koraku_ensure_usage_period(p_org_id);
  v_start := v_period.period_start;

  begin
    insert into public.koraku_usage_ledger (
      org_id, period_start, idempotency_key, credits, kind, metadata
    )
    values (
      p_org_id,
      v_start,
      p_idempotency_key,
      v_grant,
      'adjustment',
      jsonb_build_object(
        'effect', 'grant',
        'reason', coalesce(nullif(trim(p_reason), ''), 'admin grant'),
        'actor_user_id', p_actor_user_id::text
      )
    );
  exception
    when unique_violation then
      settled := false;
      select up.credits_used, up.credits_limit, up.period_end
        into credits_used, credits_limit, period_end
      from public.koraku_usage_period up
      where up.org_id = p_org_id and up.period_start = v_start;
      return next;
      return;
  end;

  update public.koraku_usage_period up
  set credits_used = greatest(0::bigint, up.credits_used - v_grant),
      updated_at = now()
  where up.org_id = p_org_id and up.period_start = v_start
  returning up.credits_used, up.credits_limit, up.period_end
  into credits_used, credits_limit, period_end;

  settled := true;
  return next;
end;
$$;

create or replace function public.koraku_admin_dashboard_stats()
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v_start date;
  v_result jsonb;
begin
  select b.period_start into v_start from public.koraku_usage_month_bounds() b;

  select jsonb_build_object(
    'period_start', v_start,
    'org_count', (select count(*)::int from public.koraku_usage_period p where p.period_start = v_start),
    'total_credits_used', coalesce((
      select sum(p.credits_used)::bigint from public.koraku_usage_period p where p.period_start = v_start
    ), 0),
    'orgs_over_80_pct', coalesce((
      select count(*)::int from public.koraku_usage_period p
      where p.period_start = v_start
        and p.credits_limit > 0
        and (p.credits_used::numeric / p.credits_limit::numeric) >= 0.8
    ), 0),
    'orgs_over_95_pct', coalesce((
      select count(*)::int from public.koraku_usage_period p
      where p.period_start = v_start
        and p.credits_limit > 0
        and (p.credits_used::numeric / p.credits_limit::numeric) >= 0.95
    ), 0),
    'recent_adjustments', coalesce((
      select jsonb_agg(row_to_json(t)::jsonb)
      from (
        select l.org_id, l.credits, l.metadata, l.created_at
        from public.koraku_usage_ledger l
        where l.kind = 'adjustment'
        order by l.created_at desc
        limit 15
      ) t
    ), '[]'::jsonb)
  ) into v_result;

  return v_result;
end;
$$;

grant execute on function public.koraku_credit_adjust(uuid, int, text, uuid, text) to service_role;
grant execute on function public.koraku_admin_dashboard_stats() to service_role;
