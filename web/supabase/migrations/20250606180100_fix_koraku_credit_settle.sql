-- Fix koraku_credit_settle: OUT column names shadowed table columns in UPDATE,
-- causing credits_used := NULL + p_credits and a NOT NULL violation (HTTP 400 via PostgREST).

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
      select up.credits_used, up.credits_limit, up.period_end
        into credits_used, credits_limit, period_end
      from public.koraku_usage_period up
      where up.org_id = p_org_id and up.period_start = v_start;
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
