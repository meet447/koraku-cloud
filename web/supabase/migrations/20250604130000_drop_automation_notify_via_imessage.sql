-- Replaced by agent IMessageSend tool (no per-automation delivery flag).

alter table public.koraku_automation
  drop column if exists notify_via_imessage;
