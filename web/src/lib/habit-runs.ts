/** Human-facing copy for habit (automation) runs — outcomes, not pipeline jargon. */

export type HabitRunLike = {
  status: string;
  trigger_summary?: string | null;
  result_summary?: string | null;
  error?: string | null;
  progress_detail?: string | null;
  outcome_label?: string | null;
};

const TOOL_PROGRESS: Record<string, string> = {
  ComposioRun: "Using your connected apps…",
  WebSearch: "Searching the web…",
  ExaSearch: "Searching the web…",
  Read: "Reading a file…",
  Write: "Writing a file…",
  Bash: "Running a command…",
  Gmail: "Checking email…",
};

export function humanizeHabitProgress(detail: string | null | undefined): string {
  const raw = (detail ?? "").trim();
  if (!raw) return "Working on it…";
  const running = raw.match(/^Running\s+([A-Za-z0-9_]+)/i);
  if (running) {
    const tool = running[1];
    return TOOL_PROGRESS[tool] ?? "Working on it…";
  }
  if (/composio/i.test(raw)) return "Using your connected apps…";
  return raw;
}

export function humanHabitRunBadge(run: HabitRunLike): string | null {
  if (run.status === "skipped") return "Skipped";
  if (run.status === "running") return "In progress";
  if (run.status === "failed") return "Needs attention";
  if (run.outcome_label === "unchanged") return "Nothing new";
  if (run.outcome_label === "changed") return "Updated";
  if (run.outcome_label === "new") return "New finding";
  if (run.status === "completed" || run.status === "succeeded") return "Done";
  return null;
}

export function humanHabitTriggerSummary(summary: string | null | undefined): string {
  const s = (summary ?? "").trim();
  if (!s) return "Background run";
  if (/^Scheduled run/i.test(s)) return "On schedule";
  if (/^Manual/i.test(s)) return "You asked Koraku to run this";
  if (/^Composio/i.test(s)) return "App event";
  return s.length > 120 ? `${s.slice(0, 119)}…` : s;
}

export type HabitLike = {
  id: string;
  title: string;
  headline?: string | null;
  status: "active" | "paused";
  consecutive_failures?: number;
  current_run_id?: string | null;
  last_run_at?: string | null;
  health_line?: string | null;
};

const DAY_MS = 86_400_000;

export function buildHabitsAwaySummary(items: HabitLike[]): {
  headline: string;
  details: string[];
} | null {
  if (items.length === 0) return null;

  const active = items.filter((h) => h.status === "active");
  const paused = items.filter((h) => h.status === "paused");
  const working = active.filter((h) => h.current_run_id);
  const troubled = items.filter((h) => (h.consecutive_failures ?? 0) >= 2 || h.health_line);
  const now = Date.now();
  const recent = items.filter((h) => {
    const t = h.last_run_at ? Date.parse(h.last_run_at) : NaN;
    return Number.isFinite(t) && now - t < DAY_MS;
  });

  const headline =
    active.length === 0
      ? paused.length > 0
        ? "All habits are paused"
        : "No background habits yet"
      : working.length > 0
        ? `Koraku is working on ${working.length} habit${working.length === 1 ? "" : "s"} for you`
        : `Watching ${active.length} habit${active.length === 1 ? "" : "s"} for you`;

  const details: string[] = [];
  if (recent.length > 0) {
    details.push(
      `${recent.length} habit${recent.length === 1 ? "" : "s"} ran in the last 24 hours`,
    );
  }
  for (const h of troubled.slice(0, 2)) {
    const name = h.headline || h.title;
    details.push(
      h.health_line ? `${name} — ${h.health_line}` : `${name} — may need a look`,
    );
  }
  if (paused.length > 0 && active.length > 0) {
    details.push(`${paused.length} paused`);
  }

  return { headline, details };
}
