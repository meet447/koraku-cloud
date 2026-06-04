"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { KorakuAppPage } from "@/components/KorakuAppPage";
import { KorakuPageHeader } from "@/components/KorakuPageHeader";
import { KorakuButton } from "@/components/KorakuButton";
import { KorakuAlert } from "@/components/KorakuAlert";
import { errorMessage } from "@/lib/error-message";

type UsagePayload = {
  configured: boolean;
  plan: string;
  credits_limit: number;
  credits_used: number;
  credits_remaining: number;
  percent_used: number;
  resets_in_days: number;
  period_end?: string;
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
    <KorakuAppPage maxWidth="3xl">
      <KorakuPageHeader
        eyebrow="Settings"
        title="Usage"
        description="Monthly credits for chat, tools, and automations on your workspace."
        action={
          <KorakuButton variant="secondary" size="sm" onClick={() => void load()} disabled={loading}>
            Refresh
          </KorakuButton>
        }
      />

      {error ? (
        <KorakuAlert variant="error" className="mt-6">
          {error}
        </KorakuAlert>
      ) : null}

      <section className="mt-8 rounded-[28px] bg-white p-6 shadow-sm ring-1 ring-neutral-200/80">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
              Credits
            </p>
            <p className="mt-2 text-2xl font-bold tabular-nums text-koraku-ink">
              {loading
                ? "…"
                : `${(data?.credits_used ?? 0).toLocaleString()} / ${(data?.credits_limit ?? 100_000).toLocaleString()}`}
            </p>
            <p className="mt-1 text-sm font-medium text-koraku-muted">Monthly limit</p>
          </div>
          <div className="text-right">
            <p className="text-sm font-semibold capitalize text-koraku-ink">
              {data?.plan ?? "free"}
            </p>
            <KorakuButton size="sm" className="mt-2" disabled>
              Upgrade
            </KorakuButton>
          </div>
        </div>

        <div className="mt-6 flex gap-1">
          {Array.from({ length: SEGMENTS }, (_, i) => (
            <div
              key={i}
              className={
                i < filledSegments
                  ? "h-8 min-w-0 flex-1 rounded-md bg-orange-500"
                  : "h-8 min-w-0 flex-1 rounded-md bg-neutral-200/80"
              }
            />
          ))}
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-sm font-medium text-koraku-muted">
          <span>{loading ? "…" : `${(data?.percent_used ?? 0).toFixed(1)}% used`}</span>
          <span>
            {loading
              ? "…"
              : data?.resets_in_days != null
                ? `Resets in ${data.resets_in_days}d`
                : "Resets monthly"}
          </span>
        </div>
      </section>

      <section className="mt-6 rounded-[28px] bg-koraku-panel p-6 ring-1 ring-neutral-200/80">
        <h2 className="text-lg font-bold text-koraku-ink">How credits work</h2>
        <ul className="mt-3 list-inside list-disc space-y-2 text-sm font-medium leading-relaxed text-koraku-muted">
          <li>Free workspaces include 100,000 credits each calendar month (UTC).</li>
          <li>Chat turns deduct credits from model tokens, tools, and image attachments.</li>
          <li>When you run out, new chats pause until the monthly reset.</li>
        </ul>
      </section>
    </KorakuAppPage>
  );
}
