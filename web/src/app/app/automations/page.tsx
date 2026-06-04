"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MoreHorizontal, Pause, Play, Plus } from "lucide-react";
import clsx from "clsx";
import { APP_BASE } from "@/lib/app-path";
import { errorMessage } from "@/lib/error-message";
import { korakuFetch, korakuFetchJson, korakuFetchOk } from "@/lib/koraku-fetch";
import { automationToolkitIconUrl } from "@/lib/toolkit-icons";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { KorakuAlert } from "@/components/KorakuAlert";
import { KorakuButton, korakuButtonClass } from "@/components/KorakuButton";
import { KorakuSearchInput } from "@/components/KorakuSearchInput";

type ConfirmKind = "create" | "delete" | "run";

type ScheduleKind = "every_n_minutes" | "daily" | "weekdays" | "weekly" | "custom";

type Automation = {
  id: string;
  title: string;
  headline: string;
  natural_language_spec: string;
  trigger_mode: "scheduled" | "event";
  status: "active" | "paused";
  timezone?: string | null;
  cron_expression?: string | null;
  event_display?: string | null;
  toolkits: string[];
  status_line?: string;
  health_line?: string;
  schedule_label?: string;
  next_run_at_computed?: string;
  last_run_at?: string | null;
  current_run_id?: string | null;
  consecutive_failures?: number;
  event_source?: "generic" | "composio";
  composio_trigger_slug?: string | null;
};

type ComposioTriggerOption = {
  slug: string;
  label: string;
  toolkit: string;
  polling?: boolean;
  description?: string;
};

type RunRow = {
  id: string;
  status: string;
  trigger_summary: string;
  result_summary: string | null;
  error: string | null;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  progress_phase?: string | null;
  progress_detail?: string | null;
  outcome_label?: string | null;
};

function buildSchedulePreset(
  kind: ScheduleKind,
  opts: { everyN: number; hour: number; minute: number; dayOfWeek: number; cron: string },
): Record<string, unknown> {
  if (kind === "custom") {
    return { kind: "custom", cron_expression: opts.cron.trim() };
  }
  if (kind === "every_n_minutes") {
    return { kind, every_n_minutes: opts.everyN };
  }
  if (kind === "weekly") {
    return { kind, hour: opts.hour, minute: opts.minute, day_of_week: opts.dayOfWeek };
  }
  return { kind, hour: opts.hour, minute: opts.minute };
}


const AUTOMATION_TEMPLATES = [
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


function formatDayLabel(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) {
    return iso;
  }
  const now = new Date();
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startThat = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const diffDays = Math.round((startThat.getTime() - startToday.getTime()) / 86400000);
  if (diffDays === 0) {
    return `Today, ${d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}`;
  }
  if (diffDays === -1) {
    return `Yesterday, ${d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}`;
  }
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function groupRuns(runs: RunRow[]): { label: string; runs: RunRow[] }[] {
  const map = new Map<string, RunRow[]>();
  for (const r of runs) {
    const dayKey = r.started_at.slice(0, 10);
    if (!map.has(dayKey)) {
      map.set(dayKey, []);
    }
    map.get(dayKey)!.push(r);
  }
  return [...map.entries()]
    .sort((a, b) => b[0].localeCompare(a[0]))
    .map(([, rs]) => ({
      label: formatDayLabel(rs[0].started_at),
      runs: rs,
    }));
}

function triggerSubtitle(a: Automation): string {
  if (a.trigger_mode === "event") {
    if (a.event_source === "composio") {
      return a.event_display || a.composio_trigger_slug || "App event";
    }
    return a.event_display || "Webhook event";
  }
  const label = a.schedule_label || a.cron_expression || "—";
  const tz = a.timezone || "UTC";
  return `${label} (${tz})`;
}

function runStatusBadge(run: RunRow): string | null {
  if (run.status === "skipped") return "Skipped";
  if (run.status === "running") return "Running";
  if (run.outcome_label === "unchanged") return "Unchanged";
  if (run.outcome_label === "changed") return "Updated";
  if (run.outcome_label === "new") return "New result";
  return null;
}

export default function AutomationsPage() {
  const [items, setItems] = useState<Automation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [runs, setRuns] = useState<RunRow[]>([]);
  const [runsLoading, setRunsLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const [pendingConfirm, setPendingConfirm] = useState<ConfirmKind | null>(null);

  const [formTitle, setFormTitle] = useState("");
  const [formHeadline, setFormHeadline] = useState("");
  const [formSpec, setFormSpec] = useState("");
  const [formTz, setFormTz] = useState("UTC");
  const [scheduleKind, setScheduleKind] = useState<ScheduleKind>("daily");
  const [scheduleEveryN, setScheduleEveryN] = useState(30);
  const [scheduleHour, setScheduleHour] = useState(9);
  const [scheduleMinute, setScheduleMinute] = useState(0);
  const [scheduleDow, setScheduleDow] = useState(5);
  const [formCron, setFormCron] = useState("0 9 * * *");
  const [formToolkits, setFormToolkits] = useState("");
  const [formTriggerMode, setFormTriggerMode] = useState<"scheduled" | "event">("scheduled");
  const [formEventSource, setFormEventSource] = useState<"generic" | "composio">("composio");
  const [composioTriggerSlug, setComposioTriggerSlug] = useState("");
  const [composioTriggerOptions, setComposioTriggerOptions] = useState<ComposioTriggerOption[]>([]);
  const [composioTriggersLoading, setComposioTriggersLoading] = useState(false);
  const [webhookReveal, setWebhookReveal] = useState<{
    id: string;
    url: string;
    token: string;
  } | null>(null);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);

  useEffect(() => {
    if (!menuOpen) return;
    function onPointerDown(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [menuOpen]);

  const loadList = useCallback(async () => {
    setError(null);
    try {
      const data = await korakuFetchJson<{ items: Automation[] }>("/koraku-api/api/automations");
      setItems(data.items ?? []);
    } catch (e) {
      setError(errorMessage(e, "Load failed"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadList();
  }, [loadList]);

  useEffect(() => {
    if (!showCreate || formTriggerMode !== "event" || formEventSource !== "composio") {
      return;
    }
    let cancelled = false;
    setComposioTriggersLoading(true);
    void (async () => {
      try {
        const data = await korakuFetchJson<{ items: ComposioTriggerOption[]; configured: boolean }>(
          "/koraku-api/api/composio/trigger-types",
        );
        if (cancelled) return;
        const items = data.items ?? [];
        setComposioTriggerOptions(items);
        if (items.length > 0 && !composioTriggerSlug) {
          setComposioTriggerSlug(items[0].slug);
        }
      } catch {
        if (!cancelled) {
          setComposioTriggerOptions([]);
        }
      } finally {
        if (!cancelled) {
          setComposioTriggersLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [showCreate, formTriggerMode, formEventSource]);

  useEffect(() => {
    try {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      if (tz) {
        setFormTz(tz);
      }
    } catch {
      /* ignore */
    }
  }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) {
      return items;
    }
    return items.filter(
      (a) =>
        a.title.toLowerCase().includes(q) ||
        a.headline.toLowerCase().includes(q) ||
        a.natural_language_spec.toLowerCase().includes(q),
    );
  }, [items, search]);

  const selected = useMemo(
    () => items.find((a) => a.id === selectedId) ?? null,
    [items, selectedId],
  );

  useEffect(() => {
    if (!selectedId && filtered.length > 0) {
      setSelectedId(filtered[0].id);
    }
    if (selectedId && !items.some((a) => a.id === selectedId) && filtered.length > 0) {
      setSelectedId(filtered[0].id);
    }
  }, [filtered, items, selectedId]);

  const loadRuns = useCallback(async (id: string) => {
    setRunsLoading(true);
    try {
      const data = await korakuFetchJson<{ items: RunRow[] }>(
        `/koraku-api/api/automations/${id}/runs`,
      );
      setRuns(data.items ?? []);
    } finally {
      setRunsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedId) {
      void loadRuns(selectedId);
    } else {
      setRuns([]);
    }
  }, [selectedId, loadRuns]);

  const pollActiveRun = selected?.current_run_id || activeRunId;
  useEffect(() => {
    if (!selectedId || !pollActiveRun) return;
    const tick = () => {
      void (async () => {
        try {
          const run = await korakuFetchJson<RunRow>(
            `/koraku-api/api/automations/${selectedId}/runs/${pollActiveRun}`,
          );
          setRuns((prev) => {
            const rest = prev.filter((r) => r.id !== run.id);
            return [run, ...rest];
          });
          if (run.status !== "running") {
            setActiveRunId(null);
            setRunning(false);
            void loadList();
          }
        } catch {
          /* ignore transient poll errors */
        }
      })();
    };
    tick();
    const id = window.setInterval(tick, 2000);
    return () => window.clearInterval(id);
  }, [selectedId, pollActiveRun, loadList]);

  function requestCreate() {
    setPendingConfirm("create");
  }

  const createSummary = useMemo(
    () =>
      [
        `Title: ${formTitle.trim() || "Untitled automation"}`,
        `Schedule: ${scheduleKind} (${formTz.trim()})`,
        formToolkits.trim() ? `Connected apps: ${formToolkits.trim()}` : "Connected apps: none specified",
        "",
        "Koraku will run this in the background. The agent can use IMessageSend when a phone is linked in External.",
      ].join("\n"),
    [formTitle, formTz, formToolkits, scheduleKind],
  );

  async function createAutomation() {
    setPendingConfirm(null);
    setSaving(true);
    setError(null);
    try {
      const toolkits = formToolkits
        .split(/[,]+/)
        .map((s) => s.trim())
        .filter(Boolean)
        .map((s) => s.toUpperCase());
      const body: Record<string, unknown> = {
        title: formTitle.trim() || "Untitled automation",
        headline: formHeadline.trim(),
        natural_language_spec: formSpec.trim(),
        trigger_mode: formTriggerMode,
        status: "active",
        toolkits,
      };
      if (formTriggerMode === "scheduled") {
        body.timezone = formTz.trim();
        body.schedule_preset = buildSchedulePreset(scheduleKind, {
          everyN: scheduleEveryN,
          hour: scheduleHour,
          minute: scheduleMinute,
          dayOfWeek: scheduleDow,
          cron: formCron,
        });
      } else {
        body.event_source = formEventSource;
        if (formEventSource === "composio") {
          if (!composioTriggerSlug) {
            throw new Error("Select an app event trigger.");
          }
          body.composio_trigger_slug = composioTriggerSlug;
        } else {
          body.event_display = "Webhook";
        }
      }
      const created = await korakuFetchJson<
        Automation & { webhook_url?: string; webhook_token?: string }
      >("/koraku-api/api/automations", {
        method: "POST",
        json: body,
      });
      if (created.webhook_url && created.webhook_token) {
        setWebhookReveal({
          id: created.id,
          url: created.webhook_url,
          token: created.webhook_token,
        });
      }
      setShowCreate(false);
      setFormTitle("");
      setFormHeadline("");
      setFormSpec("");
      await loadList();
      setSelectedId(created.id);
    } catch (e) {
      setError(errorMessage(e, "Create failed"));
    } finally {
      setSaving(false);
    }
  }

  async function setPaused(paused: boolean) {
    if (!selectedId) {
      return;
    }
    setError(null);
    try {
      await korakuFetchOk(`/koraku-api/api/automations/${selectedId}`, {
        method: "PATCH",
        json: {
          status: paused ? "paused" : "active",
          ...(paused ? {} : { reset_failure_count: true }),
        },
      });
      await loadList();
      setMenuOpen(false);
    } catch (e) {
      setError(errorMessage(e, "Update failed"));
    }
  }

  function requestDelete() {
    if (!selectedId) return;
    setPendingConfirm("delete");
  }

  async function deleteSelected() {
    setPendingConfirm(null);
    if (!selectedId) return;
    setError(null);
    try {
      await korakuFetchOk(`/koraku-api/api/automations/${selectedId}`, { method: "DELETE" });
      setSelectedId(null);
      setMenuOpen(false);
      await loadList();
    } catch (e) {
      setError(errorMessage(e, "Delete failed"));
    }
  }

  function requestRun() {
    if (!selectedId) return;
    setPendingConfirm("run");
  }

  async function runNow() {
    setPendingConfirm(null);
    if (!selectedId) return;
    setRunning(true);
    setError(null);
    try {
      const r = await korakuFetch(`/koraku-api/api/automations/${selectedId}/run`, {
        method: "POST",
      });
      let payload: { run_id?: string; status?: string } = {};
      if (r.ok) {
        try {
          payload = (await r.json()) as { run_id?: string; status?: string };
        } catch {
          payload = {};
        }
      }
      if (!r.ok) {
        let msg = await r.text();
        try {
          const j = JSON.parse(msg) as { detail?: unknown };
          if (j.detail !== undefined) {
            msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
          }
        } catch {
          /* keep msg */
        }
        throw new Error(msg || `HTTP ${r.status}`);
      }
      if (payload.run_id) {
        setActiveRunId(payload.run_id);
      }
      await loadRuns(selectedId);
      await loadList();
      if (payload.status !== "running") {
        setRunning(false);
        setActiveRunId(null);
      }
    } catch (e) {
      setError(errorMessage(e, "Run failed"));
      setRunning(false);
      setActiveRunId(null);
    }
  }

  const runGroups = useMemo(() => groupRuns(runs), [runs]);

  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="flex shrink-0 items-center justify-between border-b border-neutral-200/50 bg-white px-6 py-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.22em] text-orange-700">Automations</p>
            <h1 className="mt-1 text-xl font-bold tracking-tight text-koraku-ink">Scheduled workflows</h1>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href={APP_BASE}
              className={korakuButtonClass({ variant: "secondary", size: "sm" })}
            >
              Open chat
            </Link>
            <KorakuButton
              size="sm"
              onClick={() => setShowCreate((s) => !s)}
              className="inline-flex gap-2"
            >
              <Plus className="h-4 w-4" strokeWidth={2} />
              New
            </KorakuButton>
          </div>
        </header>

        {showCreate ? (
          <div className="shrink-0 border-b border-neutral-200/60 bg-neutral-50/80 px-6 py-5">
            <p className="text-sm font-semibold text-neutral-900">New automation</p>
            <p className="mt-1 max-w-2xl text-xs font-medium text-neutral-500">
              Automations run in the background on a schedule you define. Koraku uses your connections where needed.
            </p>
            <div className="mt-4 flex max-w-4xl flex-wrap gap-2">
              {AUTOMATION_TEMPLATES.map((template) => (
                <button
                  key={template.label}
                  type="button"
                  onClick={() => {
                    setFormTitle(template.title);
                    setFormHeadline(template.headline);
                    setFormSpec(template.spec);
                    setScheduleKind("weekdays");
                    setScheduleHour(8);
                    setScheduleMinute(0);
                    setFormCron(template.cron);
                    setFormToolkits(template.toolkits);
                  }}
                  className="rounded-full border border-orange-200 bg-orange-50 px-3 py-1.5 text-xs font-bold text-orange-800 transition hover:bg-orange-100"
                >
                  Use template: {template.label}
                </button>
              ))}
            </div>
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
                Headline (optional)
                <input
                  value={formHeadline}
                  onChange={(e) => setFormHeadline(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm font-medium text-neutral-900 outline-none focus:ring-2 focus:ring-neutral-200"
                  placeholder="Short label shown in the list"
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
                placeholder="Describe the steps, timing, and what “done” looks like."
              />
            </label>
            <label className="mt-3 block max-w-xs text-xs font-semibold uppercase tracking-wide text-neutral-500">
              Trigger
              <select
                value={formTriggerMode}
                onChange={(e) => setFormTriggerMode(e.target.value as "scheduled" | "event")}
                className="mt-1 w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm font-medium outline-none focus:ring-2 focus:ring-neutral-200"
              >
                <option value="scheduled">On a schedule</option>
                <option value="event">Webhook event</option>
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
                    <option value="composio">Connected app (Composio)</option>
                    <option value="generic">Custom webhook URL</option>
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
                        to use app event triggers. The server also needs{" "}
                        <code className="font-mono">COMPOSIO_API_KEY</code>.
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
                    {composioTriggerOptions.find((o) => o.slug === composioTriggerSlug)?.description ? (
                      <p className="mt-2 text-xs font-medium text-neutral-500">
                        {composioTriggerOptions.find((o) => o.slug === composioTriggerSlug)?.description}
                      </p>
                    ) : null}
                  </div>
                ) : (
                  <p className="mt-2 max-w-2xl text-xs font-medium leading-relaxed text-neutral-600">
                    After you save, Koraku shows a one-time webhook URL and secret token. POST JSON to that
                    URL from Zapier or your app.
                  </p>
                )}
              </>
            ) : null}
            {formTriggerMode === "scheduled" ? (
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
            {formTriggerMode === "scheduled" && scheduleKind !== "every_n_minutes" && scheduleKind !== "custom" ? (
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
                Before this automation can act through {formToolkits.trim()}, connect those apps in{" "}
                <Link href={`${APP_BASE}/connections`} className="text-orange-700 underline">
                  Connections
                </Link>
                . External sends, shares, deletes, and calendar changes should be confirmed in the automation spec.
              </p>
            ) : null}
            <div className="mt-4 flex gap-2">
              <KorakuButton
                disabled={
                  saving ||
                  !formSpec.trim() ||
                  (formTriggerMode === "event" &&
                    formEventSource === "composio" &&
                    !composioTriggerSlug)
                }
                onClick={requestCreate}
              >
                {saving ? "Saving…" : "Save automation"}
              </KorakuButton>
              <KorakuButton variant="secondary" onClick={() => setShowCreate(false)}>
                Cancel
              </KorakuButton>
            </div>
          </div>
        ) : null}

        {error ? (
          <KorakuAlert variant="error" className="mx-6 mt-3">
            {error}
          </KorakuAlert>
        ) : null}

        <div className="flex min-h-0 flex-1">
          <aside className="flex w-full max-w-sm shrink-0 flex-col border-r border-neutral-200/80 bg-neutral-50/50">
            <div className="p-3">
              <KorakuSearchInput
                variant="compact"
                value={search}
                onChange={setSearch}
                placeholder="Search automations…"
              />
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-4">
              {loading ? (
                <p className="px-2 py-6 text-center text-sm text-neutral-500">Loading…</p>
              ) : filtered.length === 0 ? (
                <div className="px-3 py-6 text-center">
                  <p className="text-sm font-semibold text-neutral-700">
                    No automations yet.
                  </p>
                  <p className="mt-1 text-xs font-medium leading-relaxed text-neutral-500">
                    Start with a daily brief, inbox summary, or weekly review template.
                    Connect apps first when an automation needs Gmail, Calendar, Slack, or files.
                  </p>
                </div>
              ) : (
                <ul className="space-y-1">
                  {filtered.map((a) => {
                    const active = a.id === selectedId;
                    return (
                      <li key={a.id}>
                        <button
                          type="button"
                          onClick={() => setSelectedId(a.id)}
                          className={clsx(
                            "flex w-full flex-col gap-1 rounded-2xl px-3 py-3 text-left transition",
                            active ? "bg-white shadow-sm ring-1 ring-neutral-200/80" : "hover:bg-white/80",
                          )}
                        >
                          <div className="flex items-center gap-2">
                            <div className="flex -space-x-1">
                              {(a.toolkits.length ? a.toolkits : ["KORAKU"]).slice(0, 4).map((tk) => (
                                /* eslint-disable-next-line @next/next/no-img-element */
                                <img
                                  key={tk}
                                  src={automationToolkitIconUrl(tk)}
                                  alt=""
                                  className="h-6 w-6 rounded-md border border-white bg-white object-contain ring-1 ring-neutral-100"
                                  width={24}
                                  height={24}
                                />
                              ))}
                            </div>
                            <span className="min-w-0 flex-1 truncate text-[13px] font-bold text-neutral-900">
                              {a.headline || a.title}
                            </span>
                          </div>
                          <span
                            className={clsx(
                              "text-[11px] font-semibold uppercase tracking-wide",
                              a.status === "paused" ? "text-neutral-500" : "text-emerald-700/90",
                            )}
                          >
                            {a.status_line || (a.status === "paused" ? "Paused" : "Active")}
                          </span>
                          <p className="line-clamp-2 text-[12px] font-medium leading-snug text-neutral-500">
                            {a.natural_language_spec}
                          </p>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </aside>

          <section className="min-h-0 min-w-0 flex-1 overflow-y-auto bg-white px-6 py-6">
            {!selected ? (
              <p className="mt-20 text-center text-sm font-medium text-neutral-500">Select an automation</p>
            ) : (
              <>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="text-lg font-bold text-neutral-900">{selected.headline || selected.title}</h2>
                      <span
                        className={clsx(
                          "rounded-full px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wide",
                          selected.status === "active"
                            ? "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200/80"
                            : "bg-neutral-100 text-neutral-600 ring-1 ring-neutral-200/80",
                        )}
                      >
                        {selected.status_line || (selected.status === "active" ? "Active" : "Paused")}
                      </span>
                      {selected.health_line ? (
                        <span className="rounded-full bg-amber-50 px-2.5 py-0.5 text-[11px] font-bold text-amber-900 ring-1 ring-amber-200/80">
                          {selected.health_line}
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-1 text-sm font-medium text-neutral-500">
                      {selected.trigger_mode === "event"
                        ? selected.event_display || "Runs when the connected event fires"
                        : `Runs on a schedule · ${triggerSubtitle(selected)}`}
                    </p>
                    {selected.next_run_at_computed ? (
                      <p className="mt-1 text-xs font-medium text-neutral-400">
                        Next run (approx.):{" "}
                        <span className="font-mono text-neutral-600">
                          {new Date(selected.next_run_at_computed).toLocaleString()}
                        </span>
                      </p>
                    ) : null}
                    {pollActiveRun ? (
                      <p className="mt-2 rounded-2xl bg-sky-50 px-3 py-2 text-xs font-semibold text-sky-900 ring-1 ring-sky-200/80">
                        Run in progress…{" "}
                        {runs.find((r) => r.id === pollActiveRun)?.progress_detail || "Working"}
                      </p>
                    ) : null}
                    {webhookReveal?.id === selected.id ? (
                      <div className="mt-3 max-w-xl rounded-2xl bg-amber-50 px-4 py-3 text-xs font-medium text-amber-950 ring-1 ring-amber-200/80">
                        <p className="font-bold uppercase tracking-wide">Webhook (copy now)</p>
                        <p className="mt-2 break-all font-mono text-[11px]">{webhookReveal.url}</p>
                        <p className="mt-2">
                          Token is only shown once. External callers POST JSON with{" "}
                          <code className="rounded bg-white/80 px-1">?token=…</code> on the URL.
                        </p>
                      </div>
                    ) : selected.trigger_mode === "event" &&
                      selected.event_source !== "composio" &&
                      webhookReveal?.id !== selected.id ? (
                      <p className="mt-2 text-xs font-medium text-neutral-500">
                        Webhook URL was issued at creation. Create a new event automation if you need a fresh token.
                      </p>
                    ) : selected.event_source === "composio" ? (
                      <p className="mt-2 text-xs font-medium text-neutral-500">
                        Runs when Composio delivers{" "}
                        {selected.composio_trigger_slug || "the configured app event"}. Pause to stop listening.
                      </p>
                    ) : null}
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <button
                      type="button"
                      disabled={running || selected.status !== "active"}
                      onClick={requestRun}
                      className="rounded-full border border-neutral-200 bg-white px-4 py-2 text-sm font-semibold text-neutral-900 shadow-sm transition hover:bg-neutral-50 disabled:opacity-40"
                    >
                      {running ? "Running…" : "Run now"}
                    </button>
                    <button
                      type="button"
                      onClick={() => void setPaused(selected.status === "active")}
                      className="inline-flex items-center gap-1.5 rounded-full border border-neutral-200 bg-white px-4 py-2 text-sm font-semibold text-neutral-900 shadow-sm transition hover:bg-neutral-50"
                    >
                      {selected.status === "active" ? (
                        <>
                          <Pause className="h-4 w-4" strokeWidth={2} />
                          Pause
                        </>
                      ) : (
                        <>
                          <Play className="h-4 w-4" strokeWidth={2} />
                          Resume
                        </>
                      )}
                    </button>
                    <div className="relative" ref={menuRef}>
                      <button
                        type="button"
                        onClick={() => setMenuOpen((o) => !o)}
                        className="flex h-9 w-9 items-center justify-center rounded-full border border-neutral-200 bg-white text-neutral-700 shadow-sm hover:bg-neutral-50"
                        aria-label="More actions"
                      >
                        <MoreHorizontal className="h-4 w-4" strokeWidth={2} />
                      </button>
                      {menuOpen ? (
                        <div className="absolute right-0 z-10 mt-1 min-w-[10rem] rounded-xl border border-neutral-200 bg-white py-1 shadow-lg">
                          <button
                            type="button"
                            onClick={requestDelete}
                            className="w-full px-3 py-2 text-left text-sm font-semibold text-red-700 hover:bg-red-50"
                          >
                            Delete…
                          </button>
                        </div>
                      ) : null}
                    </div>
                  </div>
                </div>

                <div className="mt-6 rounded-2xl border border-neutral-200/90 bg-neutral-50/80 px-4 py-4">
                  <p className="text-[13px] font-medium leading-relaxed text-neutral-700">{selected.natural_language_spec}</p>
                </div>

                <h3 className="mt-8 text-sm font-bold uppercase tracking-wide text-neutral-400">Run history</h3>
                {runsLoading ? (
                  <p className="mt-4 text-sm text-neutral-500">Loading history…</p>
                ) : runs.length === 0 ? (
                  <p className="mt-4 text-sm text-neutral-500">
                    No runs yet. Use <span className="font-semibold">Run now</span> or wait for the schedule.
                  </p>
                ) : (
                  <div className="mt-4 space-y-6">
                    {runGroups.map((g) => (
                      <div key={g.label}>
                        <p className="text-xs font-bold uppercase tracking-wide text-neutral-400">{g.label}</p>
                        <ul className="mt-2 space-y-4">
                          {g.runs.map((run) => (
                            <li
                              key={run.id}
                              className="rounded-2xl border border-neutral-200/80 bg-white px-4 py-3 shadow-[0_1px_2px_rgb(0_0_0_/0.04)]"
                            >
                              <div className="flex flex-wrap items-center gap-2">
                                <p className="text-[13px] font-semibold text-neutral-800">{run.trigger_summary}</p>
                                {runStatusBadge(run) ? (
                                  <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-neutral-600">
                                    {runStatusBadge(run)}
                                  </span>
                                ) : null}
                              </div>
                              {run.status === "running" && run.progress_detail ? (
                                <p className="mt-2 text-[12px] font-medium text-sky-800">{run.progress_detail}</p>
                              ) : null}
                              {run.status === "skipped" ? (
                                <p className="mt-2 text-[13px] font-medium text-neutral-600">{run.error || "Skipped"}</p>
                              ) : null}
                              {run.status === "failed" ? (
                                <div className="mt-2 rounded-xl bg-red-50 px-3 py-2 text-[13px] font-medium text-red-700">
                                  <p>{run.error || "Failed"}</p>
                                  <p className="mt-1 text-xs text-red-600">
                                    Check required connections, tighten the automation spec, then retry with Run now.
                                  </p>
                                </div>
                              ) : run.status !== "skipped" && run.status !== "running" ? (
                                <p className="mt-2 whitespace-pre-wrap text-[13px] font-medium leading-snug text-neutral-600">
                                  {run.result_summary || "—"}
                                </p>
                              ) : null}
                              {run.duration_ms != null ? (
                                <p className="mt-2 text-[11px] font-medium text-neutral-400">
                                  {run.status} · {run.duration_ms} ms
                                </p>
                              ) : null}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </section>
        </div>
        <ConfirmDialog
          open={pendingConfirm === "create"}
          title="Create this automation?"
          message={createSummary}
          confirmLabel="Create"
          onConfirm={() => void createAutomation()}
          onCancel={() => setPendingConfirm(null)}
        />
        <ConfirmDialog
          open={pendingConfirm === "delete"}
          title="Delete automation?"
          message="This removes the automation and all of its run history. This cannot be undone."
          confirmLabel="Delete"
          destructive
          onConfirm={() => void deleteSelected()}
          onCancel={() => setPendingConfirm(null)}
        />
        <ConfirmDialog
          open={pendingConfirm === "run"}
          title={`Run "${selected?.headline || selected?.title || "this automation"}" now?`}
          message="Koraku may use connected apps listed on the automation. Review the run history after it finishes."
          confirmLabel="Run now"
          onConfirm={() => void runNow()}
          onCancel={() => setPendingConfirm(null)}
        />
      </div>
  );
}
