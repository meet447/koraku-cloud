-- Monthly org-scoped credits (free tier: 100k credits / calendar month UTC).

create table if not exists public.koraku_usage_period (
  org_id uuid not null references public.koraku_organization (id) on delete cascade,
  period_start date not null,
  period_end timestamptz not null,
  plan text not null default 'free' check (plan in ('free', 'pro', 'team')),
  credits_limit bigint not null default 100000 check (credits_limit > 0),
  credits_used bigint not null default 0 check (credits_used >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (org_id, period_start)
);

create table if not exists public.koraku_usage_ledger (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.koraku_organization (id) on delete cascade,
  period_start date not null,
  idempotency_key text not null,
  credits int not null check (credits > 0),
  kind text not null check (kind in ('chat', 'automation', 'adjustment')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (org_id, idempotency_key)
);

create index if not exists koraku_usage_ledger_org_created_idx
  on public.koraku_usage_ledger (org_id, created_at desc);

alter table public.koraku_usage_period enable row level security;
alter table public.koraku_usage_ledger enable row level security;

create policy "koraku_usage_period_select_member"
  on public.koraku_usage_period for select
  using (
    exists (
      select 1 from public.koraku_org_member m
      where m.org_id = koraku_usage_period.org_id and m.user_id = auth.uid()
    )
  );

create policy "koraku_usage_ledger_select_member"
  on public.koraku_usage_ledger for select
  using (
    exists (
      select 1 from public.koraku_org_member m
      where m.org_id = koraku_usage_ledger.org_id and m.user_id = auth.uid()
    )
  );

-- Service role writes via backend only (no insert/update policies for authenticated).

create or replace function public.koraku_usage_month_bounds()
returns table (period_start date, period_end timestamptz)
language sql
stable
as $$
  select
    (date_trunc('month', (now() at time zone 'utc'))::date) as period_start,
    (date_trunc('month', (now() at time zone 'utc') + interval '1 month') at time zone 'utc') as period_end;
$$;

create or replace function public.koraku_ensure_usage_period(p_org_id uuid)
returns public.koraku_usage_period
language plpgsql
security definer
set search_path = public
as $$
declare
  v_start date;
  v_end timestamptz;
  v_row public.koraku_usage_period;
begin
  if p_org_id is null then
    raise exception 'org_id required';
  end if;

  select b.period_start, b.period_end into v_start, v_end
  from public.koraku_usage_month_bounds() b;

  insert into public.koraku_usage_period (org_id, period_start, period_end, plan, credits_limit, credits_used)
  values (p_org_id, v_start, v_end, 'free', 100000, 0)
  on conflict (org_id, period_start) do nothing;

  select * into v_row
  from public.koraku_usage_period p
  where p.org_id = p_org_id and p.period_start = v_start;

  return v_row;
end;
$$;

create or replace function public.koraku_credit_settle(
  p_org_id uuid,
  p_idempotency_key text,
  p_credits int,
  p_kind text,
  p_metadata jsonb default '{}'::jsonb
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
begin
  if p_org_id is null or coalesce(trim(p_idempotency_key), '') = '' then
    raise exception 'org_id and idempotency_key required';
  end if;
  if p_credits is null or p_credits <= 0 then
    raise exception 'credits must be positive';
  end if;

  v_period := public.koraku_ensure_usage_period(p_org_id);
  v_start := v_period.period_start;

  begin
    insert into public.koraku_usage_ledger (org_id, period_start, idempotency_key, credits, kind, metadata)
    values (p_org_id, v_start, p_idempotency_key, p_credits, coalesce(nullif(trim(p_kind), ''), 'chat'), coalesce(p_metadata, '{}'::jsonb));
  exception
    when unique_violation then
      settled := false;
      select p.credits_used, p.credits_limit, p.period_end
        into credits_used, credits_limit, period_end
      from public.koraku_usage_period p
      where p.org_id = p_org_id and p.period_start = v_start;
      return next;
      return;
  end;

  update public.koraku_usage_period up
  set credits_used = up.credits_used + p_credits,
      updated_at = now()
  where up.org_id = p_org_id and up.period_start = v_start
  returning up.credits_used, up.credits_limit, up.period_end
  into credits_used, credits_limit, period_end;

  settled := true;
  return next;
end;
$$;

grant execute on function public.koraku_usage_month_bounds() to service_role;
grant execute on function public.koraku_ensure_usage_period(uuid) to service_role;
grant execute on function public.koraku_credit_settle(uuid, text, int, text, jsonb) to service_role;

grant execute on function public.koraku_ensure_usage_period(uuid) to authenticated;
grant select on public.koraku_usage_period to authenticated;
grant select on public.koraku_usage_ledger to authenticated;
