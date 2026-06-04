import { describe, expect, it } from "vitest";
import { buildActivityHeatmap, hourBucketForDate } from "@/lib/usage-activity";

describe("usage-activity", () => {
  it("bins ledger rows into day and hour buckets", () => {
    const now = new Date(2026, 5, 4, 15, 0, 0);
    const model = buildActivityHeatmap(
      [
        {
          credits: 10,
          kind: "chat",
          created_at: new Date(2026, 5, 4, 15, 30, 0).toISOString(),
        },
        {
          credits: 5,
          kind: "chat",
          created_at: new Date(2026, 5, 3, 9, 0, 0).toISOString(),
        },
      ],
      { days: 7, year: 2026, now },
    );
    expect(model.maxValue).toBe(10);
    const todayIdx = model.days - 1;
    expect(model.grid[hourBucketForDate(new Date(2026, 5, 4, 15, 0, 0))][todayIdx]).toBe(10);
  });

  it("ignores entries outside the selected year", () => {
    const now = new Date(2026, 5, 4, 12, 0, 0);
    const model = buildActivityHeatmap(
      [
        {
          credits: 99,
          kind: "chat",
          created_at: new Date(2025, 5, 4, 12, 0, 0).toISOString(),
        },
      ],
      { days: 7, year: 2026, now },
    );
    expect(model.maxValue).toBe(0);
  });
});
