"use client";

import { useCallback, useEffect, useState } from "react";

type PersonalizationPayload = {
  agent_name: string;
  memory: string;
  soul: string;
};

export default function PersonalizationPage() {
  const [agentName, setAgentName] = useState("");
  const [memory, setMemory] = useState("");
  const [soul, setSoul] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const memoryItems = memory
    .split("\n")
    .map((line) => line.replace(/^[-*]\s*/, "").trim())
    .filter((line) => line && !line.startsWith("#"));
  const starterMemories = [
    "I prefer concise answers with clear next steps.",
    "Ask before sending messages, changing calendars, sharing files, or deleting data.",
    "When I ask for planning, separate must-have launch work from later polish.",
  ];

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const r = await fetch("/koraku-api/api/personalization", {
        cache: "no-store",
        credentials: "include",
      });
      if (!r.ok) {
        throw new Error(`Could not load (${r.status})`);
      }
      const data = (await r.json()) as PersonalizationPayload;
      setAgentName(data.agent_name ?? "");
      setMemory(data.memory ?? "");
      setSoul(data.soul ?? "");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Load failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function onSave() {
    setError(null);
    setSaving(true);
    setSavedAt(null);
    try {
      const r = await fetch("/koraku-api/api/personalization", {
        method: "PUT",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          agent_name: agentName,
          memory,
          soul,
        }),
      });
      if (!r.ok) {
        throw new Error(`Save failed (${r.status})`);
      }
      setSavedAt(Date.now());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  function addMemory(text: string) {
    const clean = text.trim();
    if (!clean) return;
    setMemory((prev) => {
      const lines = prev.split("\n").map((l) => l.trim());
      if (lines.some((l) => l.replace(/^[-*]\s*/, "") === clean)) return prev;
      return `${prev.trim() ? `${prev.trim()}\n` : ""}- ${clean}`;
    });
  }

  function forgetMemory(text: string) {
    setMemory((prev) =>
      prev
        .split("\n")
        .filter((line) => line.replace(/^[-*]\s*/, "").trim() !== text)
        .join("\n"),
    );
  }

  return (
    <main className="min-h-0 flex-1 overflow-y-auto px-6 py-10">
        <div className="mx-auto max-w-2xl">
          <h1 className="text-3xl font-bold tracking-tight text-koraku-ink">
            Personalization
          </h1>
          <p className="mt-2 text-sm font-medium text-koraku-muted">
            Name, preferences, and persona for your agent. When you are signed in, this is saved to your
            Koraku profile in the database (per account). Without Supabase configured on the server, the
            same fields are stored as{" "}
            <code className="rounded bg-neutral-100 px-1 py-0.5 font-mono text-[12px]">
              .koraku/Memory.md
            </code>{" "}
            and{" "}
            <code className="rounded bg-neutral-100 px-1 py-0.5 font-mono text-[12px]">
              .koraku/Soul.md
            </code>{" "}
            on the API host.
          </p>

          {error ? (
            <p
              className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm font-medium text-red-800 ring-1 ring-red-200/80"
              role="alert"
            >
              {error}
            </p>
          ) : null}

          <div className="mt-10 space-y-5">
            <section className="rounded-[22px] border border-orange-200/70 bg-orange-50/60 p-5">
              <p className="text-xs font-semibold uppercase tracking-wide text-orange-700">
                Memory review
              </p>
              <p className="mt-1 text-sm font-medium leading-relaxed text-neutral-700">
                Koraku treats saved memory as durable context. Keep stable preferences here;
                avoid secrets, one-off task details, and unverified guesses.
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                {memoryItems.length > 0 ? (
                  memoryItems.slice(0, 24).map((item) => (
                    <span
                      key={item}
                      className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 ring-1 ring-orange-200/70"
                    >
                      {item}
                      <button
                        type="button"
                        onClick={() => forgetMemory(item)}
                        className="text-neutral-400 hover:text-red-600"
                        aria-label={`Forget memory: ${item}`}
                      >
                        Forget
                      </button>
                    </span>
                  ))
                ) : (
                  <span className="text-sm font-medium text-neutral-500">
                    No saved memories yet. Add a starter below or tell Koraku “remember this” in chat.
                  </span>
                )}
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {starterMemories.map((item) => (
                  <button
                    key={item}
                    type="button"
                    onClick={() => addMemory(item)}
                    className="rounded-full border border-neutral-200 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 transition hover:bg-neutral-50"
                  >
                    Add: {item}
                  </button>
                ))}
              </div>
            </section>

            <section className="rounded-[22px] bg-koraku-panel p-5">
              <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                Your agent&apos;s name
              </p>
              <p className="mt-1 text-sm font-medium text-koraku-ink">
                They will answer to this name in conversation.
              </p>
              <input
                type="text"
                value={agentName}
                onChange={(e) => setAgentName(e.target.value)}
                placeholder="Koraku"
                disabled={loading}
                className="mt-4 w-full rounded-2xl border border-neutral-200/80 bg-white px-4 py-3 text-[15px] font-medium text-koraku-ink shadow-sm outline-none ring-0 transition placeholder:text-neutral-400 focus:border-neutral-300 focus:ring-2 focus:ring-neutral-200/80 disabled:opacity-50"
                maxLength={120}
                autoComplete="off"
              />
            </section>

            <section className="rounded-[22px] bg-koraku-panel p-5">
              <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                Memory
              </p>
              <p className="mt-1 text-sm font-medium text-koraku-ink">
                Preferences and instructions. No need to set the name here — that&apos;s handled above.
              </p>
              <textarea
                value={memory}
                onChange={(e) => setMemory(e.target.value)}
                placeholder={
                  "Preferences and instructions — e.g. 'I prefer short bullet points', 'Always cite sources'…"
                }
                disabled={loading}
                rows={8}
                className="mt-4 w-full resize-y rounded-2xl border border-neutral-200/80 bg-white px-4 py-3 text-[15px] font-medium leading-relaxed text-koraku-ink shadow-sm outline-none placeholder:text-neutral-400 focus:border-neutral-300 focus:ring-2 focus:ring-neutral-200/80 disabled:opacity-50"
              />
            </section>

            <section className="rounded-[22px] bg-koraku-panel p-5">
              <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                Soul / persona
              </p>
              <p className="mt-1 text-sm font-medium text-koraku-ink">
                Optional voice, attitude, and role — layered on top of the base Koraku behavior.
              </p>
              <textarea
                value={soul}
                onChange={(e) => setSoul(e.target.value)}
                placeholder="e.g. warm mentor, terse senior engineer, always uses nautical metaphors…"
                disabled={loading}
                rows={8}
                className="mt-4 w-full resize-y rounded-2xl border border-neutral-200/80 bg-white px-4 py-3 text-[15px] font-medium leading-relaxed text-koraku-ink shadow-sm outline-none placeholder:text-neutral-400 focus:border-neutral-300 focus:ring-2 focus:ring-neutral-200/80 disabled:opacity-50"
              />
            </section>
          </div>

          <div className="mt-8 flex flex-wrap items-center justify-end gap-3">
            {savedAt ? (
              <span className="text-xs font-medium text-koraku-muted">Saved.</span>
            ) : null}
            <button
              type="button"
              onClick={() => void onSave()}
              disabled={loading || saving}
              className="rounded-full bg-neutral-500 px-8 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-neutral-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </div>
      </main>
  );
}
