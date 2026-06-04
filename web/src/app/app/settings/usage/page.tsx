"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { SettingsPageShell } from "@/components/SettingsPageShell";
import { KorakuButton } from "@/components/KorakuButton";
import { KorakuAlert } from "@/components/KorakuAlert";
import { UsageActivityGraph } from "@/components/UsageActivityGraph";
import { errorMessage } from "@/lib/error-message";
import { korakuUi } from "@/lib/koraku-ui";
import type { UsageActivityEntry } from "@/lib/usage-activity";

type UsagePayload = {
  configured: boolean;
  plan: string;
  credits_limit: number;
  credits_used: number;
  credits_remaining: number;
  percent_used: number;
  resets_in_days: number;
  period_end?: string;
  activity?: UsageActivityEntry[];
};

const SEGMENTS = 40;

export default function SettingsUsagePage() {
  const [data, setData] = useState<UsagePayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const r = await fetch("/koraku-api/api/usage", { cache: "no-store" });
      if (!r.ok) throw new Error(`Failed to load usage (${r.status})`);
      setData((await r.json()) as UsagePayload);
    } catch (e) {
      setError(errorMessage(e, "Could not load usage"));
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filledSegments = useMemo(() => {
    if (!data) return 0;
    const pct = Math.min(100, Math.max(0, data.percent_used));
    return Math.round((pct / 100) * SEGMENTS);
  }, [data]);

  return (
    <SettingsPageShell
      title="Usage"
      description="Monthly credits for chat, tools, and automations on your workspace."
      action={
        <KorakuButton variant="secondary" size="sm" onClick={() => void load()} disabled={loading}>
          Refresh
        </KorakuButton>
      }
    >
      {error ? <KorakuAlert variant="error">{error}</KorakuAlert> : null}

      <section className={korakuUi.panel}>
        <div className="mb-3 flex items-center justify-between gap-3">
          <h2 className="text-base font-bold text-koraku-ink">Credits</h2>
          <button
            type="button"
            className="text-xs font-semibold text-koraku-muted hover:text-koraku-ink"
            disabled
          >
            View pricing
          </button>
        </div>

        <div className={korakuUi.card}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                Monthly limit
              </p>
              <p className="mt-1 text-xl font-bold tabular-nums text-koraku-ink">
                {loading
                  ? "…"
                  : `${(data?.credits_used ?? 0).toLocaleString()} / ${(data?.credits_limit ?? 100_000).toLocaleString()}`}
              </p>
            </div>
            <div className="text-right">
              <p className="text-sm font-semibold capitalize text-koraku-ink">
                {data?.plan ?? "free"}
              </p>
              <KorakuButton size="sm" className="mt-1.5" disabled>
                Upgrade
              </KorakuButton>
            </div>
          </div>

          <div className="mt-4 flex gap-0.5">
            {Array.from({ length: SEGMENTS }, (_, i) => (
              <div
                key={i}
                className={
                  i < filledSegments
                    ? "h-5 min-w-0 flex-1 rounded-sm bg-orange-500"
                    : "h-5 min-w-0 flex-1 rounded-sm bg-neutral-200/80"
                }
              />
            ))}
          </div>

          <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs font-medium text-koraku-muted">
            <span>{loading ? "…" : `${(data?.percent_used ?? 0).toFixed(2)}% used`}</span>
            <span>
              {loading
                ? "…"
                : data?.resets_in_days != null
                  ? `Resets in ${data.resets_in_days}d`
                  : "Resets monthly"}
            </span>
          </div>
        </div>
      </section>

      <UsageActivityGraph activity={data?.activity ?? []} loading={loading} compact />

      <p className="text-xs font-medium leading-relaxed text-koraku-muted">
        Free workspaces include 100,000 credits per calendar month (UTC). Chat deducts credits
        for tokens, tools, and images; new chats pause when you run out until reset.
      </p>
    </SettingsPageShell>
  );
}
