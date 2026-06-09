"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MoreHorizontal, Pause, Pencil, Play, Plus } from "lucide-react";
import clsx from "clsx";
import { APP_BASE } from "@/lib/app-path";
import { errorMessage } from "@/lib/error-message";
import { korakuFetch, korakuFetchJson, korakuFetchOk } from "@/lib/koraku-fetch";
import { automationToolkitIconUrl } from "@/lib/toolkit-icons";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { HabitFormPanel } from "@/components/HabitFormPanel";
import {
  AutomationsPageSkeleton,
  AutomationsRunHistorySkeleton,
} from "@/components/AutomationsSkeleton";
import { KorakuAlert } from "@/components/KorakuAlert";
import { KorakuButton, korakuButtonClass } from "@/components/KorakuButton";
import { KorakuSearchInput } from "@/components/KorakuSearchInput";
import { formatAutomationScheduleLabel } from "@/lib/automation-schedule";
import {
  buildSchedulePreset,
  defaultHabitFormState,
  habitToFormState,
  type ScheduleKind,
} from "@/lib/habit-form";
import {
  buildHabitsAwaySummary,
  humanHabitRunBadge,
  humanHabitTriggerSummary,
  humanizeHabitProgress,
} from "@/lib/habit-runs";

type ConfirmKind = "create" | "save-edit" | "delete" | "run";

type FormPanelMode = "create" | "edit" | null;

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
  schedule_preset?: Record<string, unknown> | null;
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
  return [...map.entries()].toSorted((a, b) => b[0].localeCompare(a[0]))
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
  const label = formatAutomationScheduleLabel(a);
  const tz = a.timezone || "UTC";
  return `${label} · ${tz}`;
}

export function AutomationsPageClient() {
  const [items, setItems] = useState<Automation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [mobileShowDetail, setMobileShowDetail] = useState(false);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [runs, setRuns] = useState<RunRow[]>([]);
  const [runsLoading, setRunsLoading] = useState(false);
  const [panelMode, setPanelMode] = useState<FormPanelMode>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
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
    if (panelMode !== "create" || formTriggerMode !== "event" || formEventSource !== "composio") {
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
  }, [panelMode, formTriggerMode, formEventSource, composioTriggerSlug]);

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

  const awaySummary = useMemo(() => buildHabitsAwaySummary(items), [items]);

  function closeFormPanel() {
    setPanelMode(null);
    setEditingId(null);
  }

  function openCreatePanel() {
    const defaults = defaultHabitFormState();
    setFormTitle(defaults.formTitle);
    setFormHeadline(defaults.formHeadline);
    setFormSpec(defaults.formSpec);
    setFormTz(defaults.formTz);
    setScheduleKind(defaults.scheduleKind);
    setScheduleEveryN(defaults.scheduleEveryN);
    setScheduleHour(defaults.scheduleHour);
    setScheduleMinute(defaults.scheduleMinute);
    setScheduleDow(defaults.scheduleDow);
    setFormCron(defaults.formCron);
    setFormToolkits(defaults.formToolkits);
    setFormTriggerMode(defaults.formTriggerMode);
    setFormEventSource(defaults.formEventSource);
    setComposioTriggerSlug(defaults.composioTriggerSlug);
    setEditingId(null);
    setPanelMode("create");
  }

  function openEditPanel(automation: Automation) {
    const state = habitToFormState(automation);
    setFormTitle(state.formTitle);
    setFormHeadline(state.formHeadline);
    setFormSpec(state.formSpec);
    setFormTz(state.formTz);
    setScheduleKind(state.scheduleKind);
    setScheduleEveryN(state.scheduleEveryN);
    setScheduleHour(state.scheduleHour);
    setScheduleMinute(state.scheduleMinute);
    setScheduleDow(state.scheduleDow);
    setFormCron(state.formCron);
    setFormToolkits(state.formToolkits);
    setFormTriggerMode(state.formTriggerMode);
    setFormEventSource(state.formEventSource);
    setComposioTriggerSlug(state.composioTriggerSlug);
    setEditingId(automation.id);
    setPanelMode("edit");
    setMenuOpen(false);
  }

  function parseToolkitsInput(): string[] {
    return formToolkits
      .split(/[,]+/)
      .map((s) => s.trim())
      .filter(Boolean)
      .map((s) => s.toUpperCase());
  }

  useEffect(() => {
    const firstId = filtered[0]?.id;
    if (!firstId) return;
    if (!selectedId || !items.some((a) => a.id === selectedId)) {
      setSelectedId(firstId);
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
    if (!selectedId) {
      setRuns([]);
      return;
    }
    let cancelled = false;
    const load = () => {
      if (cancelled) return;
      void loadRuns(selectedId);
    };
    if (typeof window.requestIdleCallback === "function") {
      const idleId = window.requestIdleCallback(load, { timeout: 1200 });
      return () => {
        cancelled = true;
        window.cancelIdleCallback(idleId);
      };
    }
    const timeoutId = globalThis.setTimeout(load, 0);
    return () => {
      cancelled = true;
      globalThis.clearTimeout(timeoutId);
    };
  }, [selectedId, loadRuns]);

  const pollActiveRun =
    selected?.status === "active" ? selected.current_run_id || activeRunId : null;
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

  function requestSaveEdit() {
    setPendingConfirm("save-edit");
  }

  const createSummary = useMemo(
    () =>
      [
        `Title: ${formTitle.trim() || "Untitled habit"}`,
        `Schedule: ${scheduleKind} (${formTz.trim()})`,
        formToolkits.trim() ? `Connected apps: ${formToolkits.trim()}` : "Connected apps: none specified",
        "",
        "Koraku will work on this in the background using your memory and connections.",
      ].join("\n"),
    [formTitle, formTz, formToolkits, scheduleKind],
  );

  const editSummary = useMemo(
    () =>
      [
        `Title: ${formTitle.trim() || "Untitled habit"}`,
        formTriggerMode === "scheduled"
          ? `Schedule: ${scheduleKind} (${formTz.trim()})`
          : "Trigger: event (unchanged)",
        "",
        "Saved changes apply to the next scheduled or manual run.",
      ].join("\n"),
    [formTitle, formTz, formTriggerMode, scheduleKind],
  );

  async function createAutomation() {
    setPendingConfirm(null);
    setSaving(true);
    setError(null);
    try {
      const toolkits = parseToolkitsInput();
      const body: Record<string, unknown> = {
        title: formTitle.trim() || "Untitled habit",
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
      closeFormPanel();
      await loadList();
      setSelectedId(created.id);
    } catch (e) {
      setError(errorMessage(e, "Create failed"));
    } finally {
      setSaving(false);
    }
  }

  async function saveHabitEdits() {
    setPendingConfirm(null);
    if (!editingId) return;
    setSaving(true);
    setError(null);
    try {
      const body: Record<string, unknown> = {
        title: formTitle.trim() || "Untitled habit",
        headline: formHeadline.trim(),
        natural_language_spec: formSpec.trim(),
        toolkits: parseToolkitsInput(),
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
      }
      await korakuFetchJson<Automation>(`/koraku-api/api/automations/${editingId}`, {
        method: "PATCH",
        json: body,
      });
      closeFormPanel();
      await loadList();
      if (selectedId === editingId) {
        void loadRuns(editingId);
      }
    } catch (e) {
      setError(errorMessage(e, "Save failed"));
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
      if (paused) {
        setActiveRunId(null);
        setRunning(false);
      }
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
            <p className="text-xs font-bold uppercase tracking-[0.22em] text-orange-700">Habits</p>
            <h1 className="mt-1 text-xl font-bold tracking-tight text-koraku-ink">Background work</h1>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href={APP_BASE}
              className={korakuButtonClass({ variant: "secondary", size: "sm" })}
            >
              Talk to Koraku
            </Link>
            <KorakuButton
              size="sm"
              onClick={() => (panelMode === "create" ? closeFormPanel() : openCreatePanel())}
              className="inline-flex gap-2"
            >
              <Plus className="h-4 w-4" strokeWidth={2} />
              New habit
            </KorakuButton>
          </div>
        </header>

        {awaySummary && !panelMode ? (
          <div className="shrink-0 border-b border-neutral-200/50 bg-orange-50/40 px-6 py-3">
            <p className="text-sm font-semibold text-neutral-900">{awaySummary.headline}</p>
            {awaySummary.details.length > 0 ? (
              <ul className="mt-1 space-y-0.5">
                {awaySummary.details.map((line) => (
                  <li key={line} className="text-xs font-medium text-neutral-600">
                    {line}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}

        {panelMode ? (
          <HabitFormPanel
            mode={panelMode}
            saving={saving}
            formTitle={formTitle}
            setFormTitle={setFormTitle}
            formHeadline={formHeadline}
            setFormHeadline={setFormHeadline}
            formSpec={formSpec}
            setFormSpec={setFormSpec}
            formTz={formTz}
            setFormTz={setFormTz}
            scheduleKind={scheduleKind}
            setScheduleKind={setScheduleKind}
            scheduleEveryN={scheduleEveryN}
            setScheduleEveryN={setScheduleEveryN}
            scheduleHour={scheduleHour}
            setScheduleHour={setScheduleHour}
            scheduleMinute={scheduleMinute}
            setScheduleMinute={setScheduleMinute}
            scheduleDow={scheduleDow}
            setScheduleDow={setScheduleDow}
            formCron={formCron}
            setFormCron={setFormCron}
            formToolkits={formToolkits}
            setFormToolkits={setFormToolkits}
            formTriggerMode={formTriggerMode}
            setFormTriggerMode={setFormTriggerMode}
            formEventSource={formEventSource}
            setFormEventSource={setFormEventSource}
            composioTriggerSlug={composioTriggerSlug}
            setComposioTriggerSlug={setComposioTriggerSlug}
            composioTriggerOptions={composioTriggerOptions}
            composioTriggersLoading={composioTriggersLoading}
            eventTriggerReadOnly={
              panelMode === "edit" && formTriggerMode === "event"
                ? items.find((h) => h.id === editingId)?.event_display ||
                  items.find((h) => h.id === editingId)?.composio_trigger_slug ||
                  "App event"
                : null
            }
            onApplyTemplate={(template) => {
              setFormTitle(template.title);
              setFormHeadline(template.headline);
              setFormSpec(template.spec);
              setScheduleKind("weekdays");
              setScheduleHour(8);
              setScheduleMinute(0);
              setFormCron(template.cron);
              setFormToolkits(template.toolkits);
            }}
            onSave={panelMode === "edit" ? requestSaveEdit : requestCreate}
            onCancel={closeFormPanel}
          />
        ) : null}

        {error ? (
          <KorakuAlert variant="error" className="mx-6 mt-3">
            {error}
          </KorakuAlert>
        ) : null}

        <div className="flex min-h-0 flex-1">
          {loading ? (
            <AutomationsPageSkeleton />
          ) : (
          <>
          <aside className={clsx(
            "w-full max-w-sm shrink-0 flex-col border-r border-neutral-200/80 bg-neutral-50/50",
            mobileShowDetail ? "hidden md:flex" : "flex"
          )}>
            <div className="p-3">
              <KorakuSearchInput
                variant="compact"
                value={search}
                onChange={setSearch}
                placeholder="Search habits…"
              />
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-4">
              {filtered.length === 0 ? (
                <div className="px-3 py-6 text-center">
                  <p className="text-sm font-semibold text-neutral-700">
                    No habits yet.
                  </p>
                  <p className="mt-1 text-xs font-medium leading-relaxed text-neutral-500">
                    Teach Koraku what to do in the background — morning briefs, inbox checks, weekly reviews.
                    Connect apps first when a habit needs Gmail, Calendar, or Slack.
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
                          onClick={() => {
                            setSelectedId(a.id);
                            setMobileShowDetail(true);
                          }}
                          className={clsx(
                            "flex w-full flex-col gap-1 rounded-2xl px-3 py-3 text-left transition",
                            active ? "bg-white shadow-sm ring-1 ring-neutral-200/80" : "hover:bg-white/80",
                          )}
                        >
                          <div className="flex items-center gap-2">
                            <div className="flex -space-x-1">
                              {(a.toolkits.length ? a.toolkits : ["KORAKU"]).slice(0, 4).map((tk) => (
                                <Image
                                  key={tk}
                                  src={automationToolkitIconUrl(tk)}
                                  alt=""
                                  className="h-6 w-6 rounded-md border border-white bg-white object-contain ring-1 ring-neutral-100"
                                  width={24}
                                  height={24}
                                  unoptimized
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

          <section className={clsx(
            "min-h-0 min-w-0 flex-1 flex-col overflow-y-auto bg-white px-4 py-6 md:px-6",
            mobileShowDetail ? "flex" : "hidden md:flex",
          )}>
            {!selected ? (
              <p className="mt-20 text-center text-sm font-medium text-neutral-500">Select a habit</p>
            ) : (
              <>
                {/* Mobile Back Button */}
                <button
                  type="button"
                  onClick={() => setMobileShowDetail(false)}
                  className="mb-4 inline-flex items-center gap-1.5 text-xs font-semibold text-neutral-500 hover:text-neutral-800 md:hidden"
                >
                  ← Back to list
                </button>
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
                        ? `When · ${selected.event_display || "something happens in a connected app"}`
                        : `Watching · ${triggerSubtitle(selected)}`}
                    </p>
                    {selected.next_run_at_computed ? (
                      <p className="mt-1 text-xs font-medium text-neutral-400">
                        Next check (approx.):{" "}
                        <span className="font-mono text-neutral-600">
                          {new Date(selected.next_run_at_computed).toLocaleString()}
                        </span>
                      </p>
                    ) : null}
                    {pollActiveRun && selected.status === "active" ? (
                      <p className="mt-2 rounded-2xl bg-sky-50 px-3 py-2 text-xs font-semibold text-sky-900 ring-1 ring-sky-200/80">
                        Koraku is on it…{" "}
                        {humanizeHabitProgress(
                          runs.find((r) => r.id === pollActiveRun)?.progress_detail,
                        )}
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
                      {running ? "Working…" : "Do this once"}
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
                            onClick={() => openEditPanel(selected)}
                            className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-semibold text-neutral-800 hover:bg-neutral-50"
                          >
                            <Pencil className="h-3.5 w-3.5" strokeWidth={2} />
                            Edit habit…
                          </button>
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

                <h3 className="mt-8 text-sm font-bold uppercase tracking-wide text-neutral-400">
                  What Koraku did
                </h3>
                {runsLoading ? (
                  <AutomationsRunHistorySkeleton />
                ) : runs.length === 0 ? (
                  <p className="mt-4 text-sm text-neutral-500">
                    Nothing yet. Use <span className="font-semibold">Do this once</span> or wait for the next
                    check.
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
                                <p className="text-[13px] font-semibold text-neutral-800">
                                  {humanHabitTriggerSummary(run.trigger_summary)}
                                </p>
                                {humanHabitRunBadge(run) ? (
                                  <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-neutral-600">
                                    {humanHabitRunBadge(run)}
                                  </span>
                                ) : null}
                              </div>
                              {run.status === "running" && run.progress_detail ? (
                                <p className="mt-2 text-[12px] font-medium text-sky-800">
                                  {humanizeHabitProgress(run.progress_detail)}
                                </p>
                              ) : null}
                              {run.status === "skipped" ? (
                                <p className="mt-2 text-[13px] font-medium text-neutral-600">{run.error || "Skipped"}</p>
                              ) : null}
                              {run.status === "failed" ? (
                                <div className="mt-2 rounded-xl bg-red-50 px-3 py-2 text-[13px] font-medium text-red-700">
                                  <p>{run.error || "Failed"}</p>
                                  <p className="mt-1 text-xs text-red-600">
                                    Check connections, refine the habit instructions, then try Do this once.
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
          </>
          )}
        </div>
        <ConfirmDialog
          open={pendingConfirm === "create"}
          title="Create this habit?"
          message={createSummary}
          confirmLabel="Create habit"
          onConfirm={() => void createAutomation()}
          onCancel={() => setPendingConfirm(null)}
        />
        <ConfirmDialog
          open={pendingConfirm === "save-edit"}
          title="Save habit changes?"
          message={editSummary}
          confirmLabel="Save"
          onConfirm={() => void saveHabitEdits()}
          onCancel={() => setPendingConfirm(null)}
        />
        <ConfirmDialog
          open={pendingConfirm === "delete"}
          title="Delete habit?"
          message="This removes the habit and everything Koraku did for it. This cannot be undone."
          confirmLabel="Delete"
          destructive
          onConfirm={() => void deleteSelected()}
          onCancel={() => setPendingConfirm(null)}
        />
        <ConfirmDialog
          open={pendingConfirm === "run"}
          title={`Run "${selected?.headline || selected?.title || "this habit"}" now?`}
          message="Koraku may use your connections for this habit. Check What Koraku did after it finishes."
          confirmLabel="Do this once"
          onConfirm={() => void runNow()}
          onCancel={() => setPendingConfirm(null)}
        />
      </div>
  );
}
