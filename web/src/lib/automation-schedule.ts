/** Human-readable label for a scheduled automation (mirrors backend schedule helpers). */
export function cronHumanLabel(cron: string | null | undefined): string {
  const raw = (cron ?? "").trim();
  if (!raw) return "—";
  const parts = raw.split(/\s+/);
  if (parts.length !== 5) return raw;

  const [minute, hour, dom, month, dow] = parts;
  const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"] as const;

  if (
    minute.startsWith("*/") &&
    hour === "*" &&
    dom === "*" &&
    month === "*" &&
    dow === "*"
  ) {
    const n = Number.parseInt(minute.slice(2), 10);
    if (Number.isFinite(n)) {
      return n === 1 ? "Every 1 minute" : `Every ${n} minutes`;
    }
  }

  if (
    minute === "0" &&
    hour.startsWith("*/") &&
    dom === "*" &&
    month === "*" &&
    dow === "*"
  ) {
    const n = Number.parseInt(hour.slice(2), 10);
    if (Number.isFinite(n)) {
      return n === 1 ? "Every 1 hour" : `Every ${n} hours`;
    }
  }

  if (dom === "*" && month === "*" && /^\d+$/.test(minute) && /^\d+$/.test(hour)) {
    const h = Number.parseInt(hour, 10);
    const m = Number.parseInt(minute, 10);
    const timeStr = `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
    if (dow === "*") return `Daily at ${timeStr}`;
    if (dow === "1-5") return `Weekdays at ${timeStr}`;
    if (/^\d+$/.test(dow)) {
      const d = Number.parseInt(dow, 10);
      if (d >= 0 && d <= 6) return `Weekly ${days[d]} ${timeStr}`;
    }
  }

  return raw;
}

type ScheduleLike = {
  schedule_label?: string | null;
  cron_expression?: string | null;
};

/** Prefer API schedule_label when readable; otherwise derive from cron. */
export function formatAutomationScheduleLabel(automation: ScheduleLike): string {
  const cron = automation.cron_expression?.trim();
  const fromCron = cron ? cronHumanLabel(cron) : null;
  const label = automation.schedule_label?.trim();

  if (fromCron && fromCron !== cron) return fromCron;
  if (label && !label.startsWith("Custom (")) return label;
  return fromCron || label || cron || "—";
}
