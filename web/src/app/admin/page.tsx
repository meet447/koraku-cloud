"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { KorakuAlert } from "@/components/KorakuAlert";
import { KorakuButton } from "@/components/KorakuButton";
import { errorMessage } from "@/lib/error-message";
import { fetchAdminDashboard, type AdminDashboardStats } from "@/lib/koraku-admin";
import { korakuUi } from "@/lib/koraku-ui";

export default function AdminDashboardPage() {
  const [stats, setStats] = useState<AdminDashboardStats | null>(null);
  const [audit, setAudit] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const data = await fetchAdminDashboard();
      setStats(data.stats ?? {});
      setAudit(data.audit ?? []);
    } catch (e) {
      setError(errorMessage(e, "Could not load dashboard"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-koraku-ink">Dashboard</h1>
          <p className="mt-1 text-sm font-medium text-koraku-muted">
            Platform usage for the current billing month (UTC).
          </p>
        </div>
        <KorakuButton variant="secondary" size="sm" onClick={() => void load()} disabled={loading}>
          Refresh
        </KorakuButton>
      </div>

      {error ? <KorakuAlert variant="error">{error}</KorakuAlert> : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Orgs (period)", value: stats?.org_count ?? "—" },
          {
            label: "Credits used (MTD)",
            value:
              stats?.total_credits_used != null
                ? stats.total_credits_used.toLocaleString()
                : "—",
          },
          { label: "Orgs ≥ 80%", value: stats?.orgs_over_80_pct ?? "—" },
          { label: "Orgs ≥ 95%", value: stats?.orgs_over_95_pct ?? "—" },
        ].map((card) => (
          <div key={card.label} className={korakuUi.card}>
            <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
              {card.label}
            </p>
            <p className="mt-2 text-2xl font-bold text-koraku-ink">{card.value}</p>
          </div>
        ))}
      </div>

      <section className={korakuUi.card}>
        <h2 className="text-base font-bold text-koraku-ink">Recent credit adjustments</h2>
        {loading ? (
          <p className="mt-3 text-sm text-koraku-muted">Loading…</p>
        ) : (stats?.recent_adjustments ?? []).length === 0 ? (
          <p className="mt-3 text-sm text-koraku-muted">No adjustments yet this period.</p>
        ) : (
          <ul className="mt-3 divide-y divide-neutral-100">
            {(stats?.recent_adjustments ?? []).map((row, i) => {
              const meta = row.metadata ?? {};
              const reason = String(meta.reason ?? "adjustment");
              return (
                <li key={`${row.org_id}-${row.created_at}-${i}`} className="py-2.5 text-sm">
                  <Link
                    href={`/admin/orgs/${row.org_id}`}
                    className="font-mono text-xs font-semibold text-koraku-ink underline"
                  >
                    {row.org_id}
                  </Link>
                  <span className="mx-2 text-koraku-muted">·</span>
                  <span className="font-semibold text-emerald-700">+{row.credits} granted</span>
                  <span className="mx-2 text-koraku-muted">·</span>
                  <span className="text-koraku-muted">{reason}</span>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section className={korakuUi.card}>
        <h2 className="text-base font-bold text-koraku-ink">Admin audit log</h2>
        {audit.length === 0 ? (
          <p className="mt-3 text-sm text-koraku-muted">No admin actions recorded yet.</p>
        ) : (
          <ul className="mt-3 max-h-80 space-y-2 overflow-y-auto text-sm">
            {audit.map((row) => (
              <li key={String(row.id)} className="rounded-lg border border-neutral-100 px-3 py-2">
                <span className="font-semibold text-koraku-ink">{String(row.action)}</span>
                <span className="text-koraku-muted">
                  {" "}
                  on {String(row.target_type)} {String(row.target_id)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
