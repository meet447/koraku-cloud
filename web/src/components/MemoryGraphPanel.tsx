"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { MemoryGraph } from "@supermemory/memory-graph";
import type { DocumentWithMemories, GraphApiDocument } from "@supermemory/memory-graph";

type GraphResponse = {
  documents: DocumentWithMemories[];
  pagination: {
    currentPage: number;
    limit: number;
    totalItems: number;
    totalPages: number;
  };
  supermemoryConfigured?: boolean;
  source?: string;
};

function toGraphDocuments(docs: DocumentWithMemories[]): GraphApiDocument[] {
  return docs.map((doc) => ({
    id: doc.id,
    title: doc.title,
    summary: doc.summary ?? null,
    documentType: doc.documentType,
    createdAt: doc.createdAt,
    updatedAt: doc.updatedAt,
    memories: doc.memories.map((m) => ({
      id: m.id,
      memory: m.memory,
      content: m.content ?? m.memory,
      isStatic: Boolean(m.isStatic),
      spaceId: m.spaceId ?? "",
      isLatest: m.isLatest ?? true,
      isForgotten: Boolean(m.isForgotten),
      forgetAfter: m.forgetAfter ?? null,
      forgetReason: m.forgetReason ?? null,
      version: m.version ?? 1,
      parentMemoryId: m.parentMemoryId ?? null,
      rootMemoryId: m.rootMemoryId ?? null,
      createdAt: m.createdAt,
      updatedAt: m.updatedAt,
      relation: m.relation ?? null,
      memoryRelations: m.memoryRelations ?? null,
      spaceContainerTag: m.spaceContainerTag ?? null,
    })),
  }));
}

type MemoryGraphPanelProps = {
  searchQuery?: string;
};

export default function MemoryGraphPanel({ searchQuery = "" }: MemoryGraphPanelProps) {
  const [documents, setDocuments] = useState<DocumentWithMemories[]>([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const fetchPage = useCallback(async (pageNum: number, append: boolean) => {
    if (pageNum === 1) setIsLoading(true);
    else setIsLoadingMore(true);
    setError(null);
    try {
      const res = await fetch(
        `/koraku-api/api/memory/graph?page=${pageNum}&limit=80`,
        { cache: "no-store", credentials: "include" },
      );
      if (!res.ok) {
        const body = await res.text();
        throw new Error(body || `Graph load failed (${res.status})`);
      }
      const data = (await res.json()) as GraphResponse;
      setDocuments((prev) =>
        append ? [...prev, ...(data.documents ?? [])] : (data.documents ?? []),
      );
      const p = data.pagination;
      setHasMore(Boolean(p && p.currentPage < p.totalPages));
      setPage(pageNum);
    } catch (e) {
      setError(e instanceof Error ? e : new Error("Could not load memory graph"));
    } finally {
      setIsLoading(false);
      setIsLoadingMore(false);
    }
  }, []);

  useEffect(() => {
    void fetchPage(1, false);
  }, [fetchPage]);

  const loadMore = useCallback(async () => {
    if (isLoadingMore || !hasMore) return;
    await fetchPage(page + 1, true);
  }, [fetchPage, hasMore, isLoadingMore, page]);

  const graphDocuments = useMemo(() => toGraphDocuments(documents), [documents]);

  const filteredDocuments = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return graphDocuments;
    return graphDocuments
      .map((doc) => {
        const title = (doc.title ?? "").toLowerCase();
        const summary = (doc.summary ?? "").toLowerCase();
        const memories = doc.memories.filter((m) => {
          const text = `${m.memory ?? ""} ${m.content ?? ""}`.toLowerCase();
          return text.includes(q) || title.includes(q) || summary.includes(q);
        });
        if (memories.length === 0 && !title.includes(q) && !summary.includes(q)) {
          return null;
        }
        return { ...doc, memories };
      })
      .filter(Boolean) as GraphApiDocument[];
  }, [graphDocuments, searchQuery]);

  const highlightIds = useMemo(
    () => (searchQuery.trim() ? filteredDocuments.map((d) => d.id) : []),
    [filteredDocuments, searchQuery],
  );

  if (error && !isLoading) {
    return (
      <section className="rounded-3xl border border-red-200 bg-red-50 px-6 py-8 text-center">
        <p className="text-sm font-semibold text-red-900">Could not load memory</p>
        <p className="mt-2 text-sm font-medium text-red-800">{error.message}</p>
        <button
          type="button"
          onClick={() => void fetchPage(1, false)}
          className="mt-4 rounded-full border border-red-300 bg-white px-4 py-2 text-sm font-semibold text-red-900 hover:bg-red-50"
        >
          Retry
        </button>
      </section>
    );
  }

  return (
    <section className="overflow-hidden rounded-3xl bg-neutral-950 ring-1 ring-neutral-800">
      <div className="flex items-center justify-between gap-3 border-b border-white/10 px-5 py-3">
        <p className="text-xs font-semibold text-white/50">
          Learned memory · pan & zoom · click nodes for detail
        </p>
        {!isLoading && !error ? (
          <span className="text-xs font-semibold text-white/40">
            {filteredDocuments.length} source{filteredDocuments.length === 1 ? "" : "s"}
          </span>
        ) : null}
      </div>
      <div className="relative h-[min(60vh,560px)] min-h-[360px] w-full bg-[#0a0a0a]">
        <MemoryGraph
          documents={filteredDocuments}
          isLoading={isLoading}
          isLoadingMore={isLoadingMore}
          hasMore={hasMore}
          onLoadMore={loadMore}
          totalCount={filteredDocuments.length}
          error={error}
          variant="consumer"
          maxNodes={400}
          highlightDocumentIds={highlightIds}
          highlightsVisible={highlightIds.length > 0}
        >
          <div className="flex h-full flex-col items-center justify-center gap-2 px-6 text-center">
            <p className="text-sm font-semibold text-white/70">No learned memories yet</p>
            <p className="max-w-sm text-xs font-medium text-white/45">
              Chat with Koraku to build memory, or add standing preferences in Personalization.
            </p>
          </div>
        </MemoryGraph>
      </div>
    </section>
  );
}
