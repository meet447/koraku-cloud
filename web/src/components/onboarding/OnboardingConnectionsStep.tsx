"use client";

import Image from "next/image";
import { useCallback, useEffect, useMemo, useState } from "react";
import clsx from "clsx";
import { errorMessage } from "@/lib/error-message";
import { korakuFetchJson } from "@/lib/koraku-fetch";
import { ONBOARDING_CONNECTION_SLUGS } from "@/lib/onboarding";
import { toolkitIconUrl } from "@/lib/toolkit-icons";
import { isToolkitEnabled } from "@/lib/connections";
import { KorakuAlert } from "@/components/KorakuAlert";
import { OnboardingConnectionsSkeleton } from "@/components/onboarding/OnboardingSkeleton";

type Overview = {
  configured: boolean;
  connections: Array<{
    status: string;
    toolkit_slug: string;
    is_disabled: boolean;
  }>;
};

type CatalogRow = {
  slug: string;
  name: string;
  description: string;
  icon_slug: string;
};

export function OnboardingConnectionsStep({ disabled = false }: { disabled?: boolean }) {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [catalogItems, setCatalogItems] = useState<CatalogRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connecting, setConnecting] = useState<string | null>(null);
  const [iconBroken, setIconBroken] = useState<Record<string, boolean>>({});

  const loadOverview = useCallback(async () => {
    try {
      setOverview(await korakuFetchJson<Overview>("/koraku-api/api/composio/overview"));
    } catch (e) {
      setError(errorMessage(e, "Could not load connections"));
    }
  }, []);

  const loadCatalog = useCallback(async () => {
    try {
      const data = await korakuFetchJson<{ items: CatalogRow[] }>(
        "/koraku-api/api/composio/toolkits",
      );
      setCatalogItems(Array.isArray(data.items) ? data.items : []);
    } catch (e) {
      setError(errorMessage(e, "Could not load integration catalog"));
      setCatalogItems([]);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      await Promise.all([loadOverview(), loadCatalog()]);
      if (!cancelled) setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [loadOverview, loadCatalog]);

  const suggested = useMemo(() => {
    const want = new Set(ONBOARDING_CONNECTION_SLUGS.map((s) => s.toUpperCase()));
    return catalogItems.filter((t) => want.has(t.slug.toUpperCase()));
  }, [catalogItems]);

  async function connectToolkit(slug: string) {
    if (!overview?.configured) {
      setError("Connections aren’t available yet. You can skip and connect later.");
      return;
    }
    setConnecting(slug);
    setError(null);
    try {
      const data = await korakuFetchJson<{ redirect_url: string | null }>(
        "/koraku-api/api/composio/connect",
        { method: "POST", json: { toolkit: slug } },
      );
      if (data.redirect_url) {
        window.open(data.redirect_url, "_blank", "noopener,noreferrer");
      }
      await loadOverview();
    } catch (e) {
      setError(errorMessage(e, "Connect failed"));
    } finally {
      setConnecting(null);
    }
  }

  if (loading) {
    return <OnboardingConnectionsSkeleton count={ONBOARDING_CONNECTION_SLUGS.length} />;
  }

  return (
    <div className="space-y-5">
      {error ? <KorakuAlert variant="error">{error}</KorakuAlert> : null}

      {overview && !overview.configured ? (
        <KorakuAlert variant="warning">
          Connections aren’t available yet. Skip for now and connect later from Connections in the app.
        </KorakuAlert>
      ) : null}

      <ul className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
        {suggested.map((toolkit) => {
          const enabled = isToolkitEnabled(overview, toolkit.slug);
          const busted = iconBroken[toolkit.slug];
          return (
            <li
              key={toolkit.slug}
              className="flex items-center gap-3 rounded-2xl border border-neutral-200/90 bg-koraku-panel px-4 py-3"
            >
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white ring-1 ring-neutral-100">
                {busted ? (
                  <span className="text-sm font-bold text-neutral-400">{toolkit.name.slice(0, 1)}</span>
                ) : (
                  <Image
                    src={toolkitIconUrl(toolkit.icon_slug)}
                    alt=""
                    width={32}
                    height={32}
                    unoptimized
                    className="h-7 w-7 object-contain"
                    onError={() => setIconBroken((prev) => ({ ...prev, [toolkit.slug]: true }))}
                  />
                )}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-bold text-koraku-ink">{toolkit.name}</p>
                <p className="text-xs font-medium text-koraku-muted line-clamp-2">
                  {toolkit.description || "Connect for chat and automations."}
                </p>
              </div>
              {enabled ? (
                <span className="shrink-0 text-xs font-semibold text-emerald-600">Connected</span>
              ) : (
                <button
                  type="button"
                  disabled={disabled || !overview?.configured || connecting === toolkit.slug}
                  onClick={() => void connectToolkit(toolkit.slug)}
                  className={clsx(
                    "shrink-0 rounded-full px-3 py-1.5 text-xs font-semibold transition",
                    overview?.configured
                      ? "bg-neutral-900 text-white hover:bg-neutral-800 disabled:opacity-50"
                      : "cursor-not-allowed bg-neutral-200 text-neutral-500",
                  )}
                >
                  {connecting === toolkit.slug ? "…" : "Connect"}
                </button>
              )}
            </li>
          );
        })}
      </ul>

      {suggested.length === 0 ? (
        <p className="text-sm font-medium text-koraku-muted">
          No suggested integrations loaded. You can connect apps later from Connections.
        </p>
      ) : null}

      <p className="text-xs font-medium text-koraku-muted">
        OAuth opens in a new tab. Return here when finished, or skip and connect anytime from{" "}
        <span className="text-koraku-ink">Connections</span>.
      </p>
    </div>
  );
}
