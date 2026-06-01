"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { APP_BASE } from "@/lib/app-path";

const BrainMemoryGraph = dynamic(() => import("@/components/BrainMemoryGraph"), {
  ssr: false,
  loading: () => (
    <section className="flex h-[min(52vh,520px)] min-h-[320px] items-center justify-center rounded-[32px] bg-neutral-950 ring-1 ring-neutral-800">
      <p className="text-sm font-semibold text-white/60">Loading memory graph…</p>
    </section>
  ),
});

type Thread = { id: string; title: string; updatedAt: string | null };
type BrainNote = { id: string; title: string; body: string; createdAt: string };

const NOTE_KEY = "koraku_brain_notes";

function readNotes(): BrainNote[] {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(NOTE_KEY) || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export default function BrainPage() {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [notes, setNotes] = useState<BrainNote[]>([]);
  const [query, setQuery] = useState("");
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setNotes(readNotes());
    const onStorage = () => setNotes(readNotes());
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  useEffect(() => {
    async function load() {
      try {
        const threadsRes = await fetch("/api/chat/threads", { cache: "no-store" });
        if (threadsRes.ok) {
          const data = (await threadsRes.json()) as { threads: Thread[] };
          setThreads(data.threads ?? []);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not load brain");
      }
    }
    void load();
  }, []);

  const filteredNotes = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return notes;
    return notes.filter((n) => `${n.title} ${n.body}`.toLowerCase().includes(q));
  }, [notes, query]);

  const filteredThreads = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return threads.slice(0, 8);
    return threads.filter((t) => t.title.toLowerCase().includes(q)).slice(0, 12);
  }, [query, threads]);

  function saveDraft() {
    const body = draft.trim();
    if (!body) return;
    const note: BrainNote = {
      id: crypto.randomUUID(),
      title: body.split("\n")[0]!.slice(0, 80),
      body,
      createdAt: new Date().toISOString(),
    };
    const next = [note, ...notes].slice(0, 100);
    window.localStorage.setItem(NOTE_KEY, JSON.stringify(next));
    setNotes(next);
    setDraft("");
  }

  return (
    <main className="min-h-0 flex-1 overflow-y-auto bg-white px-6 py-10">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-col justify-between gap-5 md:flex-row md:items-end">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.22em] text-orange-700">
              Brain
            </p>
            <h1 className="mt-2 text-4xl font-bold tracking-tight text-neutral-950">
              What Koraku can reuse.
            </h1>
            <p className="mt-3 max-w-2xl text-sm font-medium leading-relaxed text-neutral-600">
              Explore learned memory as an interactive graph. Explicit preferences live in
              Personalization; Supermemory links facts across chats.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              href={`${APP_BASE}/personalization`}
              className="rounded-full border border-neutral-200 px-5 py-2.5 text-sm font-bold text-neutral-800 transition hover:bg-neutral-50"
            >
              Personalization
            </Link>
            <Link
              href={APP_BASE}
              className="rounded-full bg-neutral-950 px-5 py-2.5 text-sm font-bold text-white"
            >
              Ask Koraku
            </Link>
          </div>
        </div>

        {error ? (
          <p className="mt-5 rounded-2xl bg-red-50 px-4 py-3 text-sm font-semibold text-red-800">
            {error}
          </p>
        ) : null}

        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search the graph, notes, and chats…"
          className="mt-8 w-full rounded-3xl border border-neutral-200 bg-neutral-50 px-5 py-4 text-sm font-semibold outline-none focus:bg-white focus:ring-2 focus:ring-orange-200"
        />

        <div className="mt-6">
          <BrainMemoryGraph searchQuery={query} />
        </div>

        <div className="mt-6 grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="rounded-[32px] bg-[#fbfaf6] p-6 ring-1 ring-neutral-200/80">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg font-bold text-neutral-950">Saved brain notes</h2>
              <span className="text-xs font-bold uppercase tracking-wide text-neutral-400">
                local beta store
              </span>
            </div>
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Save a decision, plan, reusable context, or summary…"
              rows={5}
              className="mt-4 w-full resize-y rounded-3xl border border-neutral-200 bg-white px-4 py-3 text-sm font-semibold leading-relaxed outline-none focus:ring-2 focus:ring-orange-200"
            />
            <button
              type="button"
              onClick={saveDraft}
              className="mt-3 rounded-full bg-orange-300 px-5 py-2 text-sm font-bold text-neutral-950 transition hover:bg-orange-200"
            >
              Save to brain
            </button>
            <div className="mt-6 space-y-3">
              {filteredNotes.length > 0 ? (
                filteredNotes.map((note) => (
                  <article key={note.id} className="rounded-3xl bg-white p-4 ring-1 ring-neutral-200/80">
                    <p className="text-sm font-bold text-neutral-950">{note.title}</p>
                    <p className="mt-2 whitespace-pre-wrap text-sm font-medium leading-relaxed text-neutral-600">
                      {note.body}
                    </p>
                  </article>
                ))
              ) : (
                <p className="rounded-3xl bg-white p-5 text-sm font-medium text-neutral-500 ring-1 ring-neutral-200/80">
                  No saved notes yet. Use “Save to brain” on assistant responses or add one here.
                </p>
              )}
            </div>
          </section>

          <aside className="space-y-5">
            <section className="rounded-[32px] bg-white p-6 ring-1 ring-neutral-200/80">
              <h2 className="text-lg font-bold text-neutral-950">Recent chats</h2>
              <div className="mt-4 space-y-2">
                {filteredThreads.length > 0 ? (
                  filteredThreads.map((thread) => (
                    <Link
                      key={thread.id}
                      href={APP_BASE}
                      className="block rounded-2xl bg-neutral-50 px-4 py-3 text-sm font-semibold text-neutral-700 transition hover:bg-neutral-100"
                    >
                      {thread.title || "Untitled chat"}
                    </Link>
                  ))
                ) : (
                  <p className="text-sm font-medium text-neutral-500">No chats found.</p>
                )}
              </div>
            </section>

            <section className="rounded-[32px] border border-orange-200/70 bg-orange-50 p-6">
              <h2 className="text-lg font-bold text-neutral-950">Workspace artifacts</h2>
              <p className="mt-2 text-sm font-medium leading-relaxed text-neutral-700">
                Files created by Koraku are attached to chat turns and visible in the
                Workspace panel. Ask Koraku to “save this as a note/report” when you
                want a durable artifact.
              </p>
            </section>
          </aside>
        </div>
      </div>
    </main>
  );
}
