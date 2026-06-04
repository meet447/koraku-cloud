"use client";

import { useMemo, useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/cn";
import { korakuUi } from "@/lib/koraku-ui";
import {
  ACTIVITY_HOUR_LABELS,
  ACTIVITY_WINDOW_DAYS,
  type ActivityWindowDays,
  activityYearOptions,
  buildActivityHeatmap,
  heatmapCellClass,
  heatmapCellLevel,
  type UsageActivityEntry,
} from "@/lib/usage-activity";

const CELL_HEIGHT = "0.875rem";

type UsageActivityGraphProps = {
  activity: UsageActivityEntry[];
  loading?: boolean;
  compact?: boolean;
};

export function UsageActivityGraph({
  activity,
  loading = false,
  compact = false,
}: UsageActivityGraphProps) {
  const yearOptions = useMemo(() => activityYearOptions(), []);
  const [year, setYear] = useState(() => yearOptions[0] ?? new Date().getFullYear());
  const [windowDays, setWindowDays] = useState<ActivityWindowDays>(7);

  const model = useMemo(
    () => buildActivityHeatmap(activity, { days: windowDays, year }),
    [activity, windowDays, year],
  );

  return (
    <section className={compact ? korakuUi.panel : "mt-6 rounded-2xl bg-koraku-panel p-4 ring-1 ring-neutral-200/80"}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-base font-bold text-koraku-ink">Activity</h2>
        <label className="relative inline-flex items-center">
          <span className="sr-only">Year</span>
          <select
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            className="appearance-none rounded-full bg-white py-2 pl-4 pr-9 text-sm font-semibold text-koraku-ink shadow-sm ring-1 ring-neutral-200/80"
            disabled={loading}
          >
            {yearOptions.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
          <ChevronDown
            className="pointer-events-none absolute right-3 h-4 w-4 text-koraku-muted"
            aria-hidden
          />
        </label>
      </div>

      <div className="flex gap-2">
        <div
          className="flex shrink-0 flex-col justify-between py-0.5 text-[10px] font-medium leading-none text-neutral-400"
          style={{ minHeight: `calc(${ACTIVITY_HOUR_LABELS.length} * ${CELL_HEIGHT})` }}
        >
          {ACTIVITY_HOUR_LABELS.map((label) => (
            <span key={label} className="h-4 leading-4">
              {label}
            </span>
          ))}
        </div>

        <div className="min-w-0 flex-1">
          <div
            className="overflow-x-auto rounded-xl bg-white ring-1 ring-neutral-200/60"
            aria-label="Credit usage by time of day over the selected period"
          >
            <div
              className="min-w-[320px] p-2"
              style={{
                backgroundImage: `
                  linear-gradient(to right, rgb(229 229 229 / 0.45) 1px, transparent 1px),
                  linear-gradient(to bottom, rgb(229 229 229 / 0.45) 1px, transparent 1px)
                `,
                backgroundSize: `calc(100% / ${model.days}) ${CELL_HEIGHT}`,
              }}
            >
              <div
                className="grid gap-px"
                style={{
                  gridTemplateColumns: `repeat(${model.days}, minmax(4px, 1fr))`,
                  gridTemplateRows: `repeat(${ACTIVITY_HOUR_LABELS.length}, ${CELL_HEIGHT})`,
                }}
              >
                {loading
                  ? Array.from(
                      { length: ACTIVITY_HOUR_LABELS.length * model.days },
                      (_, i) => `skeleton-${i}`,
                    ).map((key) => (
                      <div
                        key={key}
                        className="animate-pulse rounded-[2px] bg-neutral-100"
                      />
                    ))
                  : model.grid.flatMap((row, rowIdx) =>
                      row.map((value, colIdx) => {
                        const level = heatmapCellLevel(value, model.maxValue);
                        const day = new Date(model.start);
                        day.setDate(model.start.getDate() + colIdx);
                        const hour = rowIdx * 3;
                        return (
                          <div
                            key={`${rowIdx}-${colIdx}`}
                            title={
                              value > 0
                                ? `${value.toLocaleString()} credits · ${day.toLocaleDateString()} · ${ACTIVITY_HOUR_LABELS[rowIdx]} (${hour}:00–${hour + 2}:59)`
                                : `${day.toLocaleDateString()} · ${ACTIVITY_HOUR_LABELS[rowIdx]}`
                            }
                            className={cn(
                              "rounded-[2px] ring-1 ring-neutral-200/30",
                              heatmapCellClass(level),
                            )}
                          />
                        );
                      }),
                    )}
              </div>
            </div>
          </div>

          <div className="relative mt-2 h-6 text-[11px] font-medium text-neutral-400">
            {model.dayLabels.map(({ index, day }) =>
              day != null ? (
                <span
                  key={`day-label-${day}`}
                  className="absolute -translate-x-1/2 tabular-nums"
                  style={{ left: `${((index + 0.5) / model.days) * 100}%` }}
                >
                  {day}
                </span>
              ) : null,
            )}
          </div>

          <div className="relative mt-1 h-5 text-xs font-semibold text-neutral-500">
            {model.monthSpans.map(({ startIndex, label }) => (
              <span
                key={`${label}-${startIndex}`}
                className="absolute -translate-x-1/2"
                style={{ left: `${((startIndex + 0.5) / model.days) * 100}%` }}
              >
                {label}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-3 flex justify-center">
        <div
          className="flex gap-0.5 rounded-full bg-white p-0.5 shadow-sm ring-1 ring-neutral-200/80"
          aria-label="Activity range"
        >
          {ACTIVITY_WINDOW_DAYS.map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => setWindowDays(d)}
              className={cn(
                "rounded-full px-3 py-1.5 text-xs font-semibold transition-colors",
                windowDays === d
                  ? "bg-koraku-ink text-white"
                  : "text-koraku-muted hover:bg-neutral-100",
              )}
            >
              {d === 1 ? "1 day" : `${d} days`}
            </button>
          ))}
        </div>
      </div>

      {!loading && activity.length === 0 ? (
        <p className="mt-2 text-center text-xs font-medium text-koraku-muted">
          No credit usage yet in this period. Chat runs will appear here.
        </p>
      ) : null}
    </section>
  );
}
