import { describe, expect, it } from "vitest";
import {
  buildHabitsAwaySummary,
  humanHabitRunBadge,
  humanizeHabitProgress,
} from "./habit-runs";

describe("humanizeHabitProgress", () => {
  it("maps ComposioRun to friendly copy", () => {
    expect(humanizeHabitProgress("Running ComposioRun...")).toBe(
      "Using your connected apps…",
    );
  });
});

describe("humanHabitRunBadge", () => {
  it("maps outcome labels", () => {
    expect(humanHabitRunBadge({ status: "completed", outcome_label: "new" })).toBe(
      "New finding",
    );
  });
});

describe("buildHabitsAwaySummary", () => {
  it("returns null for empty list", () => {
    expect(buildHabitsAwaySummary([])).toBeNull();
  });

  it("summarizes active habits", () => {
    const s = buildHabitsAwaySummary([
      {
        id: "1",
        title: "Brief",
        status: "active",
        last_run_at: new Date().toISOString(),
      },
    ]);
    expect(s?.headline).toContain("Watching");
  });
});
