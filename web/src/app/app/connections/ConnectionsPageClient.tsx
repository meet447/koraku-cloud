"use client";

import Image from "next/image";
import { useCallback, useEffect, useMemo, useState } from "react";
import clsx from "clsx";
import { errorMessage } from "@/lib/error-message";
import { korakuFetchJson } from "@/lib/koraku-fetch";
import { toolkitIconUrl } from "@/lib/toolkit-icons";
import { KorakuAppPage } from "@/components/KorakuAppPage";
import { KorakuPageHeader } from "@/components/KorakuPageHeader";
import { KorakuAlert } from "@/components/KorakuAlert";
import { KorakuSearchInput } from "@/components/KorakuSearchInput";

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

function isToolkitEnabled(overview: Overview | null, toolkitSlug: string): boolean {
  if (!overview?.configured) {
    return false;
  }
  const u = toolkitSlug.toUpperCase();
  return overview.connections.some(
    (c) => c.toolkit_slug.toUpperCase() === u && c.status === "ACTIVE" && !c.is_disabled,
  );
}

export function ConnectionsPageClient() {
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
      setOverview(await korakuFetchJson<Overview>("/koraku-api/api/composio/overview"));
    } catch (e) {
      setError(errorMessage(e, "Load failed"));
    }
  }, []);

  const loadCatalog = useCallback(async () => {
    setCatalogLoading(true);
    setCatalogError(null);
    try {
      const data = await korakuFetchJson<{ items: CatalogRow[] }>(
        "/koraku-api/api/composio/toolkits",
      );
      setCatalogItems(Array.isArray(data.items) ? data.items : []);
    } catch (e) {
      setCatalogError(errorMessage(e, "Catalog load failed"));
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

  const pageLoading = !overview || catalogLoading;

  return (
    <KorakuAppPage maxWidth="5xl">
      <KorakuPageHeader
        eyebrow="Connections"
        title="Integrations"
        description="Link the tools your team already uses so Koraku can read context, take actions, and keep work moving—safely, from one place."
      />

      {error ? (
        <KorakuAlert variant="error" className="mt-5">
          {error}
        </KorakuAlert>
      ) : null}

      {catalogError ? (
        <KorakuAlert variant="warning" className="mt-5">
          {catalogError}
        </KorakuAlert>
      ) : null}

      <div className="mt-8">
        <KorakuSearchInput value={search} onChange={setSearch} placeholder="Search integrations" />
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
                        <Image
                          src={toolkitIconUrl(iconSlug)}
                          alt=""
                          width={44}
                          height={44}
                          unoptimized
                          className="h-8 w-8 object-contain"
                          onError={() => setIconBroken((prev) => ({ ...prev, [slug]: true }))}
                        />
                      )}
                    </div>
                    <div className="min-w-0">
                      <span className="block text-[17px] font-bold tracking-tight text-neutral-900">
                        {name}
                      </span>
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
    </KorakuAppPage>
  );
}
