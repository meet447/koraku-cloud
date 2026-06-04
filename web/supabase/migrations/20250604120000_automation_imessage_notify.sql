-- Optional delivery of automation run results via linked iMessage (SendBlue).

alter table public.koraku_automation
  add column if not exists notify_via_imessage boolean not null default false;
