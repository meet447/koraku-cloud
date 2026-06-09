"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { KorakuAlert } from "@/components/KorakuAlert";
import { KorakuButton } from "@/components/KorakuButton";
import { KorakuSearchInput } from "@/components/KorakuSearchInput";
import { errorMessage } from "@/lib/error-message";
import { searchAdminOrgs, type AdminOrgSummary } from "@/lib/koraku-admin";
import { korakuUi } from "@/lib/koraku-ui";

export default function AdminOrgsPage() {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<AdminOrgSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const search = useCallback(async () => {
    const q = query.trim();
    if (!q) {
      setItems([]);
      return;
    }
    setError(null);
    setLoading(true);
    try {
      setItems(await searchAdminOrgs(q));
    } catch (e) {
      setError(errorMessage(e, "Search failed"));
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [query]);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-koraku-ink">Organizations</h1>
        <p className="mt-1 text-sm font-medium text-koraku-muted">
          Search by user email, org ID (UUID), or org name.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <KorakuSearchInput
          value={query}
          onChange={setQuery}
          placeholder="Email, org name, or UUID…"
          className="min-w-[16rem] flex-1"
        />
        <KorakuButton onClick={() => void search()} disabled={loading || !query.trim()}>
          {loading ? "Searching…" : "Search"}
        </KorakuButton>
      </div>

      {error ? <KorakuAlert variant="error">{error}</KorakuAlert> : null}

      <div className={korakuUi.card}>
        {items.length === 0 ? (
          <p className="text-sm text-koraku-muted">
            {query.trim() ? "No organizations matched." : "Enter a query to search."}
          </p>
        ) : (
          <ul className="divide-y divide-neutral-100">
            {items.map((org) => (
              <li key={org.id}>
                <Link
                  href={`/admin/orgs/${org.id}`}
                  className="flex flex-wrap items-center justify-between gap-2 py-3 transition hover:bg-neutral-50/80"
                >
                  <div>
                    <p className="font-semibold text-koraku-ink">{org.name}</p>
                    <p className="font-mono text-xs text-neutral-500">{org.id}</p>
                    {org.matched_email ? (
                      <p className="mt-1 text-xs font-medium text-koraku-muted">
                        {org.matched_email}
                        {org.member_role ? ` · ${org.member_role}` : ""}
                      </p>
                    ) : null}
                  </div>
                  <span className="rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs font-bold uppercase text-neutral-600">
                    {org.kind}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
