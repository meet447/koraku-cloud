export type UsageActivityEntry = {
  credits: number;
  kind: string;
  created_at: string;
};

export const ACTIVITY_HOUR_LABELS = [
  "12 AM",
  "3 AM",
  "6 AM",
  "9 AM",
  "12 PM",
  "3 PM",
  "6 PM",
  "9 PM",
] as const;

export const ACTIVITY_WINDOW_DAYS = [1, 7, 30] as const;
export type ActivityWindowDays = (typeof ACTIVITY_WINDOW_DAYS)[number];

export type ActivityDayLabel = {
  index: number;
  day: number | null;
};

export type ActivityMonthSpan = {
  startIndex: number;
  label: string;
};

export type ActivityHeatmapModel = {
  days: number;
  grid: number[][];
  maxValue: number;
  start: Date;
  end: Date;
  dayLabels: ActivityDayLabel[];
  monthSpans: ActivityMonthSpan[];
};

const HOUR_BUCKETS = ACTIVITY_HOUR_LABELS.length;
const BUCKET_HOURS = 24 / HOUR_BUCKETS;

export function hourBucketForDate(d: Date): number {
  const h = d.getHours();
  return Math.min(HOUR_BUCKETS - 1, Math.floor(h / BUCKET_HOURS));
}

function startOfLocalDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

export function buildActivityHeatmap(
  entries: UsageActivityEntry[],
  options: { days?: number; year?: number; now?: Date } = {},
): ActivityHeatmapModel {
  const days = options.days ?? 7;
  const year = options.year ?? (options.now ?? new Date()).getFullYear();
  const now = options.now ?? new Date();
  const end = startOfLocalDay(now);
  const start = new Date(end);
  start.setDate(start.getDate() - (days - 1));

  const grid: number[][] = Array.from({ length: HOUR_BUCKETS }, () =>
    Array.from({ length: days }, () => 0),
  );

  for (const entry of entries) {
    const raw = entry.created_at?.trim();
    if (!raw) continue;
    const at = new Date(raw);
    if (Number.isNaN(at.getTime())) continue;
    if (at.getFullYear() !== year) continue;
    const dayStart = startOfLocalDay(at);
    if (dayStart < start || dayStart > end) continue;
    const dayIndex = Math.round(
      (dayStart.getTime() - start.getTime()) / 86_400_000,
    );
    if (dayIndex < 0 || dayIndex >= days) continue;
    const bucket = hourBucketForDate(at);
    grid[bucket][dayIndex] += Math.max(0, Number(entry.credits) || 0);
  }

  let maxValue = 0;
  for (const row of grid) {
    for (const v of row) {
      if (v > maxValue) maxValue = v;
    }
  }

  const dayLabels: ActivityDayLabel[] = [];
  for (let i = 0; i < days; i += 1) {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    const show = i === 0 || i === days - 1 || d.getDate() % 2 === 0;
    dayLabels.push({ index: i, day: show ? d.getDate() : null });
  }

  const monthSpans: ActivityMonthSpan[] = [];
  let lastMonth = -1;
  for (let i = 0; i < days; i += 1) {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    if (d.getMonth() !== lastMonth) {
      lastMonth = d.getMonth();
      monthSpans.push({
        startIndex: i,
        label: d.toLocaleString(undefined, { month: "short" }),
      });
    }
  }

  return {
    days,
    grid,
    maxValue,
    start,
    end,
    dayLabels,
    monthSpans,
  };
}

export function heatmapCellLevel(value: number, maxValue: number): 0 | 1 | 2 | 3 | 4 {
  if (value <= 0 || maxValue <= 0) return 0;
  const ratio = value / maxValue;
  if (ratio >= 0.75) return 4;
  if (ratio >= 0.5) return 3;
  if (ratio >= 0.25) return 2;
  return 1;
}

export function heatmapCellClass(level: 0 | 1 | 2 | 3 | 4): string {
  switch (level) {
    case 4:
      return "bg-orange-500";
    case 3:
      return "bg-orange-400";
    case 2:
      return "bg-orange-300";
    case 1:
      return "bg-orange-200";
    default:
      return "bg-white";
  }
}

export function activityYearOptions(now = new Date()): number[] {
  const y = now.getFullYear();
  return [y, y - 1, y - 2];
}
