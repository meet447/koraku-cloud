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
  containerTag?: string;
  supermemoryConfigured?: boolean;
  source?: string;
};

type BrainMemoryGraphProps = {
  searchQuery?: string;
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

export default function BrainMemoryGraph({ searchQuery = "" }: BrainMemoryGraphProps) {
  const [documents, setDocuments] = useState<DocumentWithMemories[]>([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [source, setSource] = useState<string | null>(null);

  const fetchPage = useCallback(async (pageNum: number, append: boolean) => {
    if (pageNum === 1) setIsLoading(true);
    else setIsLoadingMore(true);
    setError(null);
    try {
      const res = await fetch(
        `/koraku-api/api/brain/graph?page=${pageNum}&limit=80`,
        { cache: "no-store", credentials: "include" },
      );
      if (!res.ok) {
        const body = await res.text();
        throw new Error(body || `Graph load failed (${res.status})`);
      }
      const data = (await res.json()) as GraphResponse;
      setSource(data.source ?? null);
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

  const statusLine = useMemo(() => {
    if (isLoading) return "Loading your memory graph…";
    if (error) return null;
    if (source === "profile_fallback") {
      return "Showing learned profile facts — chat more to grow the live graph.";
    }
    if (source === "personalization_only") {
      return "Showing explicit preferences — enable Supermemory for auto-learned links.";
    }
    if (filteredDocuments.length === 0) {
      return "No memories yet. Chat with Koraku or add preferences under Personalization.";
    }
    return "Pan, zoom, and click nodes. Rectangles are sources; hexagons are memories.";
  }, [error, filteredDocuments.length, isLoading, source]);

  return (
    <section className="overflow-hidden rounded-[32px] bg-neutral-950 ring-1 ring-neutral-800">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-5 py-4">
        <div>
          <h2 className="text-lg font-bold text-white">Memory graph</h2>
          {statusLine ? (
            <p className="mt-1 text-xs font-medium text-white/55">{statusLine}</p>
          ) : null}
        </div>
        {!isLoading && !error ? (
          <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-semibold text-white/80">
            {filteredDocuments.length} document
            {filteredDocuments.length === 1 ? "" : "s"}
          </span>
        ) : null}
      </div>
      <div className="relative h-[min(52vh,520px)] min-h-[320px] w-full bg-[#0c0c0c]">
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
            <p className="text-sm font-semibold text-white/70">No memories to visualize yet</p>
            <p className="max-w-sm text-xs font-medium text-white/45">
              Koraku builds this graph from Supermemory as you chat. Save explicit preferences
              under Personalization to seed the graph.
            </p>
          </div>
        </MemoryGraph>
      </div>
    </section>
  );
}
