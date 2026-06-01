"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { APP_BASE } from "@/lib/app-path";

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

  return (
    <main className="min-h-0 flex-1 overflow-y-auto px-6 py-10">
      <div className="mx-auto max-w-2xl">
        <h1 className="text-3xl font-bold tracking-tight text-koraku-ink">
          Personalization
        </h1>
        <p className="mt-2 text-sm font-medium leading-relaxed text-koraku-muted">
          Explicit profile text injected into every chat: what to call the agent, standing
          preferences, and persona. Facts learned automatically across chats live under{" "}
          <Link href={`${APP_BASE}/memory`} className="font-semibold text-koraku-ink underline">
            Memory
          </Link>
          .
        </p>

        {error ? (
          <p
            className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm font-medium text-red-800 ring-1 ring-red-200/80"
            role="alert"
          >
            {error}
          </p>
        ) : null}

        <div className="mt-8 space-y-5">
          <section className="rounded-2xl border border-neutral-200/80 bg-koraku-panel p-5">
            <label className="block text-xs font-semibold uppercase tracking-wide text-neutral-500">
              Agent name
            </label>
            <input
              type="text"
              value={agentName}
              onChange={(e) => setAgentName(e.target.value)}
              placeholder="Koraku"
              disabled={loading}
              className="mt-3 w-full rounded-2xl border border-neutral-200/80 bg-white px-4 py-3 text-[15px] font-medium text-koraku-ink outline-none focus:border-neutral-300 focus:ring-2 focus:ring-neutral-200/80 disabled:opacity-50"
              maxLength={120}
              autoComplete="off"
            />
          </section>

          <section className="rounded-2xl border border-neutral-200/80 bg-koraku-panel p-5">
            <label className="block text-xs font-semibold uppercase tracking-wide text-neutral-500">
              Preferences
            </label>
            <p className="mt-1 text-sm font-medium text-neutral-600">
              Standing instructions and stable facts you want in every conversation.
            </p>
            <textarea
              value={memory}
              onChange={(e) => setMemory(e.target.value)}
              placeholder={
                "- Prefer concise answers with clear next steps\n- Ask before sending email or changing calendars"
              }
              disabled={loading}
              rows={10}
              className="mt-3 w-full resize-y rounded-2xl border border-neutral-200/80 bg-white px-4 py-3 text-[15px] font-medium leading-relaxed text-koraku-ink outline-none focus:border-neutral-300 focus:ring-2 focus:ring-neutral-200/80 disabled:opacity-50"
            />
          </section>

          <section className="rounded-2xl border border-neutral-200/80 bg-koraku-panel p-5">
            <label className="block text-xs font-semibold uppercase tracking-wide text-neutral-500">
              Persona
            </label>
            <p className="mt-1 text-sm font-medium text-neutral-600">
              Optional tone and style layered on top of base Koraku behavior.
            </p>
            <textarea
              value={soul}
              onChange={(e) => setSoul(e.target.value)}
              placeholder="e.g. warm mentor, direct and practical, no fluff"
              disabled={loading}
              rows={6}
              className="mt-3 w-full resize-y rounded-2xl border border-neutral-200/80 bg-white px-4 py-3 text-[15px] font-medium leading-relaxed text-koraku-ink outline-none focus:border-neutral-300 focus:ring-2 focus:ring-neutral-200/80 disabled:opacity-50"
            />
          </section>
        </div>

        <div className="mt-8 flex flex-wrap items-center justify-end gap-3">
          {savedAt ? (
            <span className="text-xs font-medium text-koraku-muted">Saved</span>
          ) : null}
          <button
            type="button"
            onClick={() => void onSave()}
            disabled={loading || saving}
            className="rounded-full bg-neutral-900 px-8 py-2.5 text-sm font-semibold text-white transition hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </main>
  );
}
