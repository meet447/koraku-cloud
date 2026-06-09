"use client";

import Link from "next/link";
import { APP_BASE } from "@/lib/app-path";
import type { ScheduleKind } from "@/lib/habit-form";
import { KorakuButton } from "@/components/KorakuButton";

const HABIT_TEMPLATES = [
  {
    label: "Daily brief",
    title: "Daily brief",
    headline: "Morning calendar and inbox brief",
    spec: "Every weekday morning, review today's calendar and important inbox items, then summarize priorities, conflicts, and follow-ups. Do not send or modify anything without explicit confirmation.",
    cron: "0 8 * * 1-5",
    toolkits: "GMAIL, GOOGLECALENDAR",
  },
  {
    label: "Inbox summary",
    title: "Inbox summary",
    headline: "Summarize unread important email",
    spec: "Summarize unread important emails, group them by action needed, and draft suggested replies without sending them.",
    cron: "0 17 * * 1-5",
    toolkits: "GMAIL",
  },
  {
    label: "Weekly review",
    title: "Weekly review",
    headline: "Weekly second-brain review",
    spec: "Every Friday, review recent notes, chats, and tasks. Produce a short review with wins, open loops, decisions, and next-week priorities.",
    cron: "0 16 * * 5",
    toolkits: "",
  },
] as const;

type ComposioTriggerOption = {
  slug: string;
  label: string;
  polling?: boolean;
  description?: string;
};

export type HabitFormPanelProps = {
  mode: "create" | "edit";
  saving: boolean;
  formTitle: string;
  setFormTitle: (v: string) => void;
  formHeadline: string;
  setFormHeadline: (v: string) => void;
  formSpec: string;
  setFormSpec: (v: string) => void;
  formTz: string;
  setFormTz: (v: string) => void;
  scheduleKind: ScheduleKind;
  setScheduleKind: (v: ScheduleKind) => void;
  scheduleEveryN: number;
  setScheduleEveryN: (v: number) => void;
  scheduleHour: number;
  setScheduleHour: (v: number) => void;
  scheduleMinute: number;
  setScheduleMinute: (v: number) => void;
  scheduleDow: number;
  setScheduleDow: (v: number) => void;
  formCron: string;
  setFormCron: (v: string) => void;
  formToolkits: string;
  setFormToolkits: (v: string) => void;
  formTriggerMode: "scheduled" | "event";
  setFormTriggerMode: (v: "scheduled" | "event") => void;
  formEventSource: "generic" | "composio";
  setFormEventSource: (v: "generic" | "composio") => void;
  composioTriggerSlug: string;
  setComposioTriggerSlug: (v: string) => void;
  composioTriggerOptions: ComposioTriggerOption[];
  composioTriggersLoading: boolean;
  eventTriggerReadOnly?: string | null;
  onApplyTemplate: (template: (typeof HABIT_TEMPLATES)[number]) => void;
  onSave: () => void;
  onCancel: () => void;
};

export function HabitFormPanel({
  mode,
  saving,
  formTitle,
  setFormTitle,
  formHeadline,
  setFormHeadline,
  formSpec,
  setFormSpec,
  formTz,
  setFormTz,
  scheduleKind,
  setScheduleKind,
  scheduleEveryN,
  setScheduleEveryN,
  scheduleHour,
  setScheduleHour,
  scheduleMinute,
  setScheduleMinute,
  scheduleDow,
  setScheduleDow,
  formCron,
  setFormCron,
  formToolkits,
  setFormToolkits,
  formTriggerMode,
  setFormTriggerMode,
  formEventSource,
  setFormEventSource,
  composioTriggerSlug,
  setComposioTriggerSlug,
  composioTriggerOptions,
  composioTriggersLoading,
  eventTriggerReadOnly,
  onApplyTemplate,
  onSave,
  onCancel,
}: HabitFormPanelProps) {
  const isEdit = mode === "edit";
  const triggerLocked = isEdit;

  return (
    <div className="shrink-0 border-b border-neutral-200/60 bg-neutral-50/80 px-6 py-5">
      <p className="text-sm font-semibold text-neutral-900">
        {isEdit ? "Edit habit" : "New habit"}
      </p>
      <p className="mt-1 max-w-2xl text-xs font-medium text-neutral-500">
        {isEdit
          ? "Refine what Koraku does in the background — schedule, instructions, and linked apps."
          : "Habits run while you’re away. Koraku remembers your preferences and uses your connections when needed."}
      </p>
      {!isEdit ? (
        <div className="mt-4 flex max-w-4xl flex-wrap gap-2">
          {HABIT_TEMPLATES.map((template) => (
            <button
              key={template.label}
              type="button"
              onClick={() => onApplyTemplate(template)}
              className="rounded-full border border-orange-200 bg-orange-50 px-3 py-1.5 text-xs font-bold text-orange-800 transition hover:bg-orange-100"
            >
              Start with: {template.label}
            </button>
          ))}
        </div>
      ) : null}
      <div className="mt-4 grid max-w-3xl gap-3 sm:grid-cols-2">
        <label className="block text-xs font-semibold uppercase tracking-wide text-neutral-500">
          Title
          <input
            value={formTitle}
            onChange={(e) => setFormTitle(e.target.value)}
            className="mt-1 w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm font-medium text-neutral-900 outline-none focus:ring-2 focus:ring-neutral-200"
            placeholder="e.g. Morning summary"
          />
        </label>
        <label className="block text-xs font-semibold uppercase tracking-wide text-neutral-500">
          Short label (optional)
          <input
            value={formHeadline}
            onChange={(e) => setFormHeadline(e.target.value)}
            className="mt-1 w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm font-medium text-neutral-900 outline-none focus:ring-2 focus:ring-neutral-200"
            placeholder="Shown in the list"
          />
        </label>
      </div>
      <label className="mt-3 block max-w-3xl text-xs font-semibold uppercase tracking-wide text-neutral-500">
        What should Koraku do?
        <textarea
          value={formSpec}
          onChange={(e) => setFormSpec(e.target.value)}
          rows={4}
          className="mt-1 w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm font-medium text-neutral-900 outline-none focus:ring-2 focus:ring-neutral-200"
          placeholder="Describe the steps and what “done” looks like. Ask Koraku to confirm before sending email or changing calendars."
        />
      </label>
      {triggerLocked ? (
        eventTriggerReadOnly ? (
          <p className="mt-3 max-w-2xl text-xs font-medium text-neutral-600">
            Trigger: <span className="font-semibold text-neutral-800">{eventTriggerReadOnly}</span>{" "}
            (create a new habit to change the trigger)
          </p>
        ) : null
      ) : (
        <>
          <label className="mt-3 block max-w-xs text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Trigger
            <select
              value={formTriggerMode}
              onChange={(e) => setFormTriggerMode(e.target.value as "scheduled" | "event")}
              className="mt-1 w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm font-medium outline-none focus:ring-2 focus:ring-neutral-200"
            >
              <option value="scheduled">On a schedule</option>
              <option value="event">When something happens</option>
            </select>
          </label>
          {formTriggerMode === "event" ? (
            <>
              <label className="mt-3 block max-w-xs text-xs font-semibold uppercase tracking-wide text-neutral-500">
                Event type
                <select
                  value={formEventSource}
                  onChange={(e) =>
                    setFormEventSource(e.target.value as "generic" | "composio")
                  }
                  className="mt-1 w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm font-medium outline-none focus:ring-2 focus:ring-neutral-200"
                >
                  <option value="composio">Connected app</option>
                  <option value="generic">Custom webhook</option>
                </select>
              </label>
              {formEventSource === "composio" ? (
                <div className="mt-3 max-w-xl">
                  {composioTriggersLoading ? (
                    <p className="text-xs font-medium text-neutral-500">Loading triggers…</p>
                  ) : composioTriggerOptions.length === 0 ? (
                    <p className="rounded-2xl bg-amber-50 px-4 py-3 text-xs font-medium text-amber-950 ring-1 ring-amber-200/80">
                      Connect Gmail in{" "}
                      <Link href={`${APP_BASE}/connections`} className="text-orange-700 underline">
                        Connections
                      </Link>{" "}
                      to use app event triggers.
                    </p>
                  ) : (
                    <label className="block text-xs font-semibold uppercase tracking-wide text-neutral-500">
                      When this happens
                      <select
                        value={composioTriggerSlug}
                        onChange={(e) => setComposioTriggerSlug(e.target.value)}
                        className="mt-1 w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm font-medium outline-none focus:ring-2 focus:ring-neutral-200"
                      >
                        {composioTriggerOptions.map((opt) => (
                          <option key={opt.slug} value={opt.slug}>
                            {opt.label}
                            {opt.polling ? " (may lag a few minutes)" : ""}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}
                </div>
              ) : (
                <p className="mt-2 max-w-2xl text-xs font-medium leading-relaxed text-neutral-600">
                  After you save, Koraku shows a one-time webhook URL and secret token.
                </p>
              )}
            </>
          ) : null}
        </>
      )}
      {(triggerLocked ? formTriggerMode === "scheduled" : formTriggerMode === "scheduled") ? (
        <div className="mt-3 grid max-w-3xl gap-3 sm:grid-cols-2">
          <label className="block text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Timezone
            <input
              value={formTz}
              onChange={(e) => setFormTz(e.target.value)}
              className="mt-1 w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 font-mono text-sm outline-none focus:ring-2 focus:ring-neutral-200"
              placeholder="e.g. America/New_York"
            />
          </label>
          <label className="block text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Schedule
            <select
              value={scheduleKind}
              onChange={(e) => setScheduleKind(e.target.value as ScheduleKind)}
              className="mt-1 w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm font-medium outline-none focus:ring-2 focus:ring-neutral-200"
            >
              <option value="every_n_minutes">Every N minutes</option>
              <option value="daily">Every day</option>
              <option value="weekdays">Weekdays</option>
              <option value="weekly">Weekly</option>
              <option value="custom">Custom cron</option>
            </select>
          </label>
        </div>
      ) : null}
      {formTriggerMode === "scheduled" && scheduleKind === "every_n_minutes" ? (
        <label className="mt-3 block max-w-xs text-xs font-semibold uppercase tracking-wide text-neutral-500">
          Interval (minutes)
          <input
            type="number"
            min={1}
            max={59}
            value={scheduleEveryN}
            onChange={(e) => setScheduleEveryN(Number(e.target.value) || 30)}
            className="mt-1 w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-neutral-200"
          />
        </label>
      ) : null}
      {formTriggerMode === "scheduled" &&
      scheduleKind !== "every_n_minutes" &&
      scheduleKind !== "custom" ? (
        <div className="mt-3 flex max-w-md flex-wrap gap-3">
          <label className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Hour
            <input
              type="number"
              min={0}
              max={23}
              value={scheduleHour}
              onChange={(e) => setScheduleHour(Number(e.target.value))}
              className="mt-1 w-20 rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm"
            />
          </label>
          <label className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Minute
            <input
              type="number"
              min={0}
              max={59}
              value={scheduleMinute}
              onChange={(e) => setScheduleMinute(Number(e.target.value))}
              className="mt-1 w-20 rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm"
            />
          </label>
          {scheduleKind === "weekly" ? (
            <label className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
              Day (0=Sun)
              <input
                type="number"
                min={0}
                max={6}
                value={scheduleDow}
                onChange={(e) => setScheduleDow(Number(e.target.value))}
                className="mt-1 w-20 rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm"
              />
            </label>
          ) : null}
        </div>
      ) : null}
      {formTriggerMode === "scheduled" && scheduleKind === "custom" ? (
        <label className="mt-3 block max-w-3xl text-xs font-semibold uppercase tracking-wide text-neutral-500">
          Cron (5 fields)
          <input
            value={formCron}
            onChange={(e) => setFormCron(e.target.value)}
            className="mt-1 w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 font-mono text-sm outline-none focus:ring-2 focus:ring-neutral-200"
            placeholder="minute hour day month weekday"
          />
        </label>
      ) : null}
      <label className="mt-3 block max-w-xl text-xs font-semibold uppercase tracking-wide text-neutral-500">
        Linked apps (optional)
        <input
          value={formToolkits}
          onChange={(e) => setFormToolkits(e.target.value)}
          className="mt-1 w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-neutral-200"
          placeholder="Optional — comma-separated labels"
        />
      </label>
      {formToolkits.trim() ? (
        <p className="mt-2 max-w-2xl rounded-2xl bg-white px-4 py-3 text-xs font-semibold leading-relaxed text-neutral-600 ring-1 ring-neutral-200/80">
          Connect {formToolkits.trim()} in{" "}
          <Link href={`${APP_BASE}/connections`} className="text-orange-700 underline">
            Connections
          </Link>{" "}
          before Koraku can act through them.
        </p>
      ) : null}
      <div className="mt-4 flex gap-2">
        <KorakuButton
          disabled={
            saving ||
            !formSpec.trim() ||
            (!isEdit &&
              formTriggerMode === "event" &&
              formEventSource === "composio" &&
              !composioTriggerSlug)
          }
          onClick={onSave}
        >
          {saving ? "Saving…" : isEdit ? "Save changes" : "Create habit"}
        </KorakuButton>
        <KorakuButton variant="secondary" onClick={onCancel}>
          Cancel
        </KorakuButton>
      </div>
    </div>
  );
}
