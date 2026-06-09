"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { KorakuAlert } from "@/components/KorakuAlert";
import { KorakuButton } from "@/components/KorakuButton";
import { errorMessage } from "@/lib/error-message";
import {
  fetchAdminOrg,
  fetchAdminOrgLedger,
  grantOrgCredits,
  updateOrgAdminState,
  updateOrgPeriod,
  type AdminOrgDetail,
  type LedgerEntry,
} from "@/lib/koraku-admin";
import { korakuUi } from "@/lib/koraku-ui";

export default function AdminOrgDetailPage() {
  const params = useParams();
  const orgId = String(params.orgId ?? "");

  const [detail, setDetail] = useState<AdminOrgDetail | null>(null);
  const [ledger, setLedger] = useState<LedgerEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [grantAmount, setGrantAmount] = useState("5000");
  const [grantReason, setGrantReason] = useState("");
  const [limitInput, setLimitInput] = useState("");
  const [planInput, setPlanInput] = useState("free");
  const [notes, setNotes] = useState("");
  const [suspendReason, setSuspendReason] = useState("");

  const load = useCallback(async () => {
    if (!orgId) return;
    setError(null);
    setLoading(true);
    try {
      const [d, l] = await Promise.all([fetchAdminOrg(orgId), fetchAdminOrgLedger(orgId)]);
      setDetail(d);
      setLedger(l);
      setLimitInput(String(d.usage.credits_limit));
      setPlanInput(d.usage.plan);
      setNotes(d.admin_state?.notes ?? "");
      setSuspendReason(d.admin_state?.suspend_reason ?? "");
    } catch (e) {
      setError(errorMessage(e, "Could not load organization"));
      setDetail(null);
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function onGrant() {
    if (!orgId) return;
    setSaving(true);
    setError(null);
    try {
      const amount = parseInt(grantAmount, 10);
      if (!Number.isFinite(amount) || amount <= 0) throw new Error("Enter a positive grant amount.");
      await grantOrgCredits(orgId, { grant_credits: amount, reason: grantReason.trim() });
      setGrantReason("");
      await load();
    } catch (e) {
      setError(errorMessage(e, "Grant failed"));
    } finally {
      setSaving(false);
    }
  }

  async function onUpdatePeriod() {
    if (!orgId) return;
    setSaving(true);
    setError(null);
    try {
      const lim = parseInt(limitInput, 10);
      if (!Number.isFinite(lim) || lim <= 0) throw new Error("Enter a valid credit limit.");
      await updateOrgPeriod(orgId, { credits_limit: lim, plan: planInput });
      await load();
    } catch (e) {
      setError(errorMessage(e, "Update failed"));
    } finally {
      setSaving(false);
    }
  }

  async function onToggleSuspend(suspended: boolean) {
    if (!orgId) return;
    setSaving(true);
    setError(null);
    try {
      await updateOrgAdminState(orgId, {
        suspended,
        suspend_reason: suspendReason,
        notes,
      });
      await load();
    } catch (e) {
      setError(errorMessage(e, "Suspend update failed"));
    } finally {
      setSaving(false);
    }
  }

  if (loading && !detail) {
    return <p className="text-sm text-koraku-muted">Loading organization…</p>;
  }

  if (!detail) {
    return (
      <div className="space-y-3">
        {error ? <KorakuAlert variant="error">{error}</KorakuAlert> : null}
        <Link href="/admin/orgs" className="text-sm font-semibold underline">
          ← Back to search
        </Link>
      </div>
    );
  }

  const usage = detail.usage;
  const pct = Math.min(100, usage.percent_used);

  return (
    <div className="space-y-6">
      <div>
        <Link href="/admin/orgs" className="text-xs font-semibold text-koraku-muted hover:text-koraku-ink">
          ← Organizations
        </Link>
        <h1 className="mt-2 text-xl font-bold text-koraku-ink">{detail.org.name}</h1>
        <p className="font-mono text-xs text-neutral-500">{detail.org.id}</p>
        {detail.admin_state?.suspended ? (
          <p className="mt-2 text-sm font-bold text-red-700">Suspended — chat blocked</p>
        ) : null}
      </div>

      {error ? <KorakuAlert variant="error">{error}</KorakuAlert> : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <section className={korakuUi.card}>
          <h2 className="text-base font-bold text-koraku-ink">Credits (current month)</h2>
          <p className="mt-2 text-2xl font-bold text-koraku-ink">
            {usage.credits_used.toLocaleString()} / {usage.credits_limit.toLocaleString()}
          </p>
          <p className="mt-1 text-sm text-koraku-muted">
            {pct.toFixed(1)}% used · resets in {usage.resets_in_days} days
          </p>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-neutral-100">
            <div className="h-full rounded-full bg-neutral-800" style={{ width: `${pct}%` }} />
          </div>

          <div className="mt-4 space-y-3 border-t border-neutral-100 pt-4">
            <p className={korakuUi.fieldLabel}>Grant credits</p>
            <div className="flex flex-wrap gap-2">
              <input
                type="number"
                value={grantAmount}
                onChange={(e) => setGrantAmount(e.target.value)}
                className={korakuUi.input}
                placeholder="Amount"
                min={1}
              />
              <input
                type="text"
                value={grantReason}
                onChange={(e) => setGrantReason(e.target.value)}
                className={`${korakuUi.input} min-w-[12rem] flex-1`}
                placeholder="Reason (support ticket, etc.)"
              />
              <KorakuButton size="sm" onClick={() => void onGrant()} disabled={saving}>
                Grant
              </KorakuButton>
            </div>
            <p className="text-xs text-koraku-muted">
              Reduces credits_used (bonus headroom). Logged as adjustment in the ledger.
            </p>
          </div>

          <div className="mt-4 space-y-3 border-t border-neutral-100 pt-4">
            <p className={korakuUi.fieldLabel}>Plan & limit</p>
            <div className="flex flex-wrap gap-2">
              <select
                value={planInput}
                onChange={(e) => setPlanInput(e.target.value)}
                className={korakuUi.input}
              >
                <option value="free">free</option>
                <option value="pro">pro</option>
                <option value="team">team</option>
              </select>
              <input
                type="number"
                value={limitInput}
                onChange={(e) => setLimitInput(e.target.value)}
                className={korakuUi.input}
                min={1}
              />
              <KorakuButton variant="secondary" size="sm" onClick={() => void onUpdatePeriod()} disabled={saving}>
                Save
              </KorakuButton>
            </div>
          </div>
        </section>

        <section className={korakuUi.card}>
          <h2 className="text-base font-bold text-koraku-ink">Org state</h2>
          <label className="mt-3 block text-sm font-medium text-koraku-ink">
            Internal notes
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              className={`${korakuUi.textarea} mt-1`}
            />
          </label>
          <label className="mt-3 block text-sm font-medium text-koraku-ink">
            Suspend reason
            <input
              type="text"
              value={suspendReason}
              onChange={(e) => setSuspendReason(e.target.value)}
              className={`${korakuUi.input} mt-1`}
            />
          </label>
          <div className="mt-4 flex flex-wrap gap-2">
            {detail.admin_state?.suspended ? (
              <KorakuButton variant="secondary" size="sm" onClick={() => void onToggleSuspend(false)} disabled={saving}>
                Unsuspend
              </KorakuButton>
            ) : (
              <KorakuButton variant="destructive" size="sm" onClick={() => void onToggleSuspend(true)} disabled={saving}>
                Suspend org
              </KorakuButton>
            )}
          </div>

          <div className="mt-6 border-t border-neutral-100 pt-4">
            <p className={korakuUi.fieldLabel}>Counts</p>
            <ul className="mt-2 space-y-1 text-sm text-koraku-muted">
              {Object.entries(detail.counts).map(([k, v]) => (
                <li key={k}>
                  {k.replace(/_/g, " ")}: <span className="font-semibold text-koraku-ink">{v}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="mt-4 border-t border-neutral-100 pt-4">
            <p className={korakuUi.fieldLabel}>Members</p>
            <ul className="mt-2 space-y-1 text-sm">
              {detail.members.map((m) => (
                <li key={m.user_id} className="font-mono text-xs text-neutral-600">
                  {m.user_id} · {m.role}
                  {m.is_default ? " · default" : ""}
                </li>
              ))}
            </ul>
          </div>
        </section>
      </div>

      <section className={korakuUi.card}>
        <h2 className="text-base font-bold text-koraku-ink">Usage ledger</h2>
        {ledger.length === 0 ? (
          <p className="mt-2 text-sm text-koraku-muted">No ledger entries this period.</p>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-neutral-100 text-xs uppercase text-neutral-500">
                  <th className="py-2 pr-4">When</th>
                  <th className="py-2 pr-4">Kind</th>
                  <th className="py-2 pr-4">Credits</th>
                  <th className="py-2">Details</th>
                </tr>
              </thead>
              <tbody>
                {ledger.map((row) => (
                  <tr key={row.id} className="border-b border-neutral-50">
                    <td className="py-2 pr-4 whitespace-nowrap text-koraku-muted">
                      {new Date(row.created_at).toLocaleString()}
                    </td>
                    <td className="py-2 pr-4 font-medium">{row.kind}</td>
                    <td className="py-2 pr-4 font-semibold">{row.credits}</td>
                    <td className="py-2 font-mono text-xs text-neutral-500">
                      {row.kind === "adjustment"
                        ? String((row.metadata as Record<string, unknown>)?.reason ?? "")
                        : String((row.metadata as Record<string, unknown>)?.run_id ?? row.idempotency_key)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
