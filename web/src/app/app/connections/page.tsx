"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import clsx from "clsx";
import { supabaseAuthHeaders } from "@/lib/supabase/fetch-auth";

type Overview = {
  configured: boolean;
  user_id: string | null;
  connections: Array<{
    id: string;
    status: string;
    toolkit_slug: string;
    toolkit_name: string;
    is_disabled: boolean;
  }>;
  active_toolkits: string[];
};

type CategoryId = "all" | "dev" | "collab" | "docs";

type CatalogRow = {
  slug: string;
  name: string;
  description: string;
  category: Exclude<CategoryId, "all">;
  icon_slug: string;
};

const CATEGORIES: { id: CategoryId; label: string }[] = [
  { id: "all", label: "All" },
  { id: "dev", label: "Developer" },
  { id: "collab", label: "Collaboration" },
  { id: "docs", label: "Docs & files" },
];

/** Simple Icons CDN: omitting the color uses each brand’s default hex from the icon set. */
function iconUrl(iconSlug: string) {
  return `https://cdn.simpleicons.org/${encodeURIComponent(iconSlug)}`;
}

function isToolkitEnabled(overview: Overview | null, toolkitSlug: string): boolean {
  if (!overview?.configured) {
    return false;
  }
  const u = toolkitSlug.toUpperCase();
  return overview.connections.some(
    (c) => c.toolkit_slug.toUpperCase() === u && c.status === "ACTIVE" && !c.is_disabled,
  );
}

export default function ConnectionsPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [catalogItems, setCatalogItems] = useState<CatalogRow[]>([]);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<CategoryId>("all");
  const [connecting, setConnecting] = useState<string | null>(null);
  const [iconBroken, setIconBroken] = useState<Record<string, boolean>>({});

  const loadOverview = useCallback(async () => {
    setError(null);
    try {
      const r = await fetch("/koraku-api/api/composio/overview", {
        cache: "no-store",
        headers: await supabaseAuthHeaders(),
      });
      if (!r.ok) {
        throw new Error(`Overview failed (${r.status})`);
      }
      setOverview((await r.json()) as Overview);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Load failed");
    }
  }, []);

  const loadCatalog = useCallback(async () => {
    setCatalogLoading(true);
    setCatalogError(null);
    try {
      const r = await fetch("/koraku-api/api/composio/toolkits", {
        cache: "no-store",
        headers: await supabaseAuthHeaders(),
      });
      if (!r.ok) {
        throw new Error(`Catalog failed (${r.status})`);
      }
      const data = (await r.json()) as { items: CatalogRow[] };
      setCatalogItems(Array.isArray(data.items) ? data.items : []);
    } catch (e) {
      setCatalogError(e instanceof Error ? e.message : "Catalog load failed");
      setCatalogItems([]);
    } finally {
      setCatalogLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadOverview();
    void loadCatalog();
  }, [loadOverview, loadCatalog]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return catalogItems.filter((t) => {
      if (category !== "all" && t.category !== category) {
        return false;
      }
      if (!q) {
        return true;
      }
      return (
        t.name.toLowerCase().includes(q) ||
        t.slug.toLowerCase().includes(q) ||
        t.description.toLowerCase().includes(q)
      );
    });
  }, [catalogItems, category, search]);

  async function connectToolkit(slug: string) {
    if (!overview?.configured) {
      setError("Integrations aren’t enabled for this workspace yet.");
      return;
    }
    setConnecting(slug);
    setError(null);
    try {
      const r = await fetch("/koraku-api/api/composio/connect", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(await supabaseAuthHeaders()),
        },
        body: JSON.stringify({ toolkit: slug }),
      });
      if (!r.ok) {
        const detail = await r.text();
        throw new Error(detail || `Connect failed (${r.status})`);
      }
      const data = (await r.json()) as { redirect_url: string | null };
      if (data.redirect_url) {
        window.open(data.redirect_url, "_blank", "noopener,noreferrer");
      }
      await loadOverview();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Connect failed");
    } finally {
      setConnecting(null);
    }
  }

  const pageLoading = !overview || catalogLoading;

  return (
    <main className="min-h-0 flex-1 overflow-y-auto bg-white px-6 py-10">
      <div className="mx-auto max-w-5xl">
        <h1 className="text-[2rem] font-bold leading-tight tracking-tight text-neutral-900">Connections</h1>
        <p className="mt-2 max-w-2xl text-sm font-medium leading-relaxed text-neutral-500">
          Link the tools your team already uses so Koraku can read context, take actions, and keep work moving—safely,
          from one place.
        </p>

        {error ? (
          <p
            className="mt-5 rounded-2xl bg-red-50 px-4 py-3 text-sm font-medium text-red-800 ring-1 ring-red-200/80"
            role="alert"
          >
            {error}
          </p>
        ) : null}

        {catalogError ? (
          <p
            className="mt-5 rounded-2xl bg-amber-50 px-4 py-3 text-sm font-medium text-amber-950 ring-1 ring-amber-200/80"
            role="status"
          >
            {catalogError}
          </p>
        ) : null}

        <div className="mt-8">
          <div className="relative min-w-0">
            <Search
              className="pointer-events-none absolute left-4 top-1/2 h-[18px] w-[18px] -translate-y-1/2 text-neutral-400"
              strokeWidth={2}
              aria-hidden
            />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search integrations"
              className="w-full rounded-full border border-neutral-200/90 bg-neutral-50/80 py-3.5 pl-11 pr-5 text-[15px] font-medium text-neutral-900 shadow-sm outline-none transition placeholder:text-neutral-400 focus:border-neutral-300 focus:bg-white focus:ring-2 focus:ring-neutral-200/80"
            />
          </div>
        </div>

        <div className="mt-5 flex flex-wrap gap-2 border-b border-neutral-200/80 pb-4">
          {CATEGORIES.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => setCategory(c.id)}
              className={clsx(
                "rounded-full px-4 py-2 text-[13px] font-semibold transition",
                category === c.id
                  ? "bg-neutral-900 text-white"
                  : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200/80 hover:text-neutral-900",
              )}
            >
              {c.label}
            </button>
          ))}
        </div>

        {pageLoading ? (
          <p className="mt-12 text-center text-sm font-medium text-neutral-500">Loading integrations…</p>
        ) : (
          <>
            {overview && !overview.configured ? (
              <p className="mt-6 rounded-2xl border border-amber-200/80 bg-amber-50/90 px-4 py-3 text-sm font-medium text-amber-950">
                Integrations aren’t enabled for this workspace yet. You can still browse popular options below;
                connecting will turn on once your administrator completes setup.
              </p>
            ) : null}

            <ul className="mt-8 grid gap-5 sm:grid-cols-2">
              {filtered.map((toolkit) => {
                const { slug, name, description, icon_slug: iconSlug } = toolkit;
                const enabled = isToolkitEnabled(overview, slug);
                const busted = iconBroken[slug];
                return (
                  <li
                    key={slug}
                    className="flex flex-col overflow-hidden rounded-2xl border border-neutral-200/90 bg-white shadow-[0_1px_3px_rgb(0_0_0_/0.04)]"
                  >
                    <div className="flex items-center gap-3 px-4 pb-3 pt-4">
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-white ring-1 ring-neutral-100">
                        {busted ? (
                          <span className="text-lg font-bold text-neutral-400" aria-hidden>
                            {name.slice(0, 1)}
                          </span>
                        ) : (
                          /* eslint-disable-next-line @next/next/no-img-element */
                          <img
                            src={iconUrl(iconSlug)}
                            alt=""
                            width={44}
                            height={44}
                            className="h-8 w-8 object-contain"
                            onError={() => setIconBroken((prev) => ({ ...prev, [slug]: true }))}
                          />
                        )}
                      </div>
                      <div className="min-w-0">
                        <span className="block text-[17px] font-bold tracking-tight text-neutral-900">{name}</span>
                      </div>
                    </div>
                    <div className="mt-auto flex min-h-[4.5rem] items-stretch justify-between gap-3 bg-neutral-100 px-4 py-3">
                      <p className="min-w-0 flex-1 text-[13px] font-medium leading-snug text-neutral-600 line-clamp-3">
                        {description || "Connect so Koraku can use this in chat and automations."}
                      </p>
                      {enabled ? (
                        <span className="shrink-0 self-center text-[13px] font-semibold text-emerald-600">
                          Connected
                        </span>
                      ) : (
                        <button
                          type="button"
                          disabled={!overview?.configured || connecting === slug}
                          onClick={() => void connectToolkit(slug)}
                          className="shrink-0 self-center text-[13px] font-semibold text-neutral-900 underline-offset-2 hover:underline disabled:cursor-not-allowed disabled:opacity-40 disabled:no-underline"
                        >
                          {connecting === slug ? "…" : "Connect"}
                        </button>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>

            {filtered.length === 0 ? (
              <p className="mt-8 text-center text-sm font-medium text-neutral-500">
                No integrations match this search or category. Try a different term or choose All.
              </p>
            ) : null}
          </>
        )}
      </div>
    </main>
  );
}
