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

type ImessageDelivery = {
  configured: boolean;
  linked: boolean;
  available: boolean;
};

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
  notify_via_imessage?: boolean;
  status_line?: string;
  delivery_line?: string;
  next_run_at_computed?: string;
  last_run_at?: string | null;
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
};


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
    return a.event_display || "Event trigger";
  }
  const cr = a.cron_expression || "—";
  const tz = a.timezone || "UTC";
  return `${cr} (${tz})`;
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
  const [formCron, setFormCron] = useState("0 9 * * *");
  const [formToolkits, setFormToolkits] = useState("");
  const [formNotifyImessage, setFormNotifyImessage] = useState(false);
  const [imessage, setImessage] = useState<ImessageDelivery>({
    configured: false,
    linked: false,
    available: false,
  });

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
      const data = await korakuFetchJson<{
        items: Automation[];
        imessage?: ImessageDelivery;
      }>("/koraku-api/api/automations");
      setItems(data.items ?? []);
      if (data.imessage) {
        setImessage(data.imessage);
      }
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

  function requestCreate() {
    setPendingConfirm("create");
  }

  const createSummary = useMemo(
    () =>
      [
        `Title: ${formTitle.trim() || "Untitled automation"}`,
        `Trigger: ${formCron.trim()} (${formTz.trim()})`,
        formToolkits.trim() ? `Connected apps: ${formToolkits.trim()}` : "Connected apps: none specified",
        formNotifyImessage ? "Results: send via iMessage when each run finishes" : "Results: in-app run history only",
        "",
        "Koraku will run this in the background. It should still ask for confirmation before high-impact external actions.",
      ].join("\n"),
    [formTitle, formCron, formTz, formToolkits, formNotifyImessage],
  );

  const imessageNotifyBlocked = formNotifyImessage && !imessage.available;

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
      const body = {
        title: formTitle.trim() || "Untitled automation",
        headline: formHeadline.trim(),
        natural_language_spec: formSpec.trim(),
        trigger_mode: "scheduled",
        status: "active",
        timezone: formTz.trim(),
        cron_expression: formCron.trim(),
        toolkits,
        notify_via_imessage: formNotifyImessage,
      };
      const created = await korakuFetchJson<Automation>("/koraku-api/api/automations", {
        method: "POST",
        json: body,
      });
      setShowCreate(false);
      setFormTitle("");
      setFormHeadline("");
      setFormSpec("");
      setFormNotifyImessage(false);
      await loadList();
      setSelectedId(created.id);
    } catch (e) {
      setError(errorMessage(e, "Create failed"));
    } finally {
      setSaving(false);
    }
  }

  async function setNotifyImessage(enabled: boolean) {
    if (!selectedId) {
      return;
    }
    if (enabled && !imessage.available) {
      setError(
        imessage.configured
          ? "iMessage is not linked. Open External to link your phone first."
          : "iMessage delivery is not available on this server.",
      );
      return;
    }
    setError(null);
    try {
      await korakuFetchOk(`/koraku-api/api/automations/${selectedId}`, {
        method: "PATCH",
        json: { notify_via_imessage: enabled },
      });
      await loadList();
    } catch (e) {
      setError(errorMessage(e, "Update failed"));
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
        json: { status: paused ? "paused" : "active" },
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
      await loadRuns(selectedId);
      await loadList();
    } catch (e) {
      setError(errorMessage(e, "Run failed"));
    } finally {
      setRunning(false);
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
                Schedule (cron)
                <input
                  value={formCron}
                  onChange={(e) => setFormCron(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 font-mono text-sm outline-none focus:ring-2 focus:ring-neutral-200"
                  placeholder="minute hour day month weekday"
                />
              </label>
            </div>
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
            <label className="mt-4 flex max-w-3xl cursor-pointer items-start gap-3 rounded-2xl border border-neutral-200/80 bg-white px-4 py-3">
              <input
                type="checkbox"
                checked={formNotifyImessage}
                onChange={(e) => setFormNotifyImessage(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-neutral-300"
              />
              <span className="text-sm font-medium text-neutral-800">
                Send run results via iMessage
                <span className="mt-0.5 block text-xs font-medium text-neutral-500">
                  After each run, Koraku texts a short summary to your linked phone.
                </span>
              </span>
            </label>
            {formNotifyImessage && !imessage.linked ? (
              <p className="mt-2 max-w-3xl rounded-2xl bg-amber-50 px-4 py-3 text-xs font-semibold leading-relaxed text-amber-900 ring-1 ring-amber-200/80">
                iMessage is not linked.{" "}
                <Link href={`${APP_BASE}/external`} className="text-amber-950 underline">
                  Link your phone in External
                </Link>{" "}
                before saving with iMessage delivery.
              </p>
            ) : null}
            {formNotifyImessage && imessage.linked && !imessage.configured ? (
              <p className="mt-2 max-w-3xl rounded-2xl bg-amber-50 px-4 py-3 text-xs font-semibold text-amber-900 ring-1 ring-amber-200/80">
                iMessage delivery is not configured on this Koraku server (SendBlue).
              </p>
            ) : null}
            <div className="mt-4 flex gap-2">
              <KorakuButton
                disabled={saving || !formSpec.trim() || imessageNotifyBlocked}
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
                        {selected.status === "active" ? "Active" : "Paused"}
                      </span>
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
                    <label className="mt-4 flex max-w-xl cursor-pointer items-start gap-3 rounded-2xl border border-neutral-200/80 bg-neutral-50/80 px-4 py-3">
                      <input
                        type="checkbox"
                        checked={Boolean(selected.notify_via_imessage)}
                        onChange={(e) => void setNotifyImessage(e.target.checked)}
                        className="mt-0.5 h-4 w-4 rounded border-neutral-300"
                      />
                      <span className="text-sm font-medium text-neutral-800">
                        Send run results via iMessage
                        {selected.delivery_line ? (
                          <span className="mt-0.5 block text-xs font-semibold text-emerald-800">
                            {selected.delivery_line}
                          </span>
                        ) : (
                          <span className="mt-0.5 block text-xs font-medium text-neutral-500">
                            Off — results stay in run history below.
                          </span>
                        )}
                      </span>
                    </label>
                    {selected.notify_via_imessage && !imessage.linked ? (
                      <p className="mt-2 max-w-xl rounded-2xl bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-900 ring-1 ring-amber-200/80">
                        iMessage is not linked — delivery will fail until you{" "}
                        <Link href={`${APP_BASE}/external`} className="underline">
                          link your phone
                        </Link>
                        .
                      </p>
                    ) : null}
                    {selected.trigger_mode === "event" ? (
                      <p className="mt-2 rounded-2xl bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800 ring-1 ring-amber-200/80">
                        Event triggers are not available yet. Use Run now or recreate this automation on a schedule.
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
                              <p className="text-[13px] font-semibold text-neutral-800">{run.trigger_summary}</p>
                              {run.status === "failed" ? (
                                <div className="mt-2 rounded-xl bg-red-50 px-3 py-2 text-[13px] font-medium text-red-700">
                                  <p>{run.error || "Failed"}</p>
                                  <p className="mt-1 text-xs text-red-600">
                                    Check required connections, tighten the automation spec, then retry with Run now.
                                  </p>
                                </div>
                              ) : (
                                <p className="mt-2 whitespace-pre-wrap text-[13px] font-medium leading-snug text-neutral-600">
                                  {run.result_summary || "—"}
                                </p>
                              )}
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
