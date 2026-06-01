"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type ProviderBlock = {
  id: string;
  label?: string;
  configured: boolean;
  default_model: string;
  models: string[];
  entries?: { id: string; label?: string }[];
};

type ChatModelsResponse = {
  active_provider?: string;
  default_model?: string;
  providers?: ProviderBlock[];
};

export default function ModelsPage() {
  const [catalog, setCatalog] = useState<ChatModelsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch("/koraku-api/api/chat-models");
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const data = (await r.json()) as ChatModelsResponse;
        if (!cancelled) setCatalog(data);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Could not load models");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const providers = catalog?.providers ?? [];

  return (
    <main className="min-h-0 flex-1 overflow-y-auto px-6 py-10">
      <div className="mx-auto max-w-2xl">
        <h1 className="text-3xl font-bold tracking-tight text-koraku-ink">
          Models
        </h1>
        <p className="mt-2 text-sm font-medium text-koraku-muted">
          Providers and models loaded from your Python API configuration (
          <code className="font-mono">.env</code>). Pick a model in the chat
          composer; configure keys here on the server.
        </p>

        {error ? (
          <p className="mt-8 rounded-2xl bg-amber-50 px-4 py-3 text-sm font-medium text-amber-950 ring-1 ring-amber-200/80">
            {error}. Is the Koraku API running?
          </p>
        ) : null}

        <section className="mt-10 space-y-4">
          {providers.length === 0 && !error ? (
            <p className="text-sm font-medium text-koraku-muted">Loading…</p>
          ) : null}

          {providers.map((block) => {
            const title = block.label?.trim() || block.id;
            const rows = block.entries?.length
              ? block.entries
              : block.models.map((id) => ({ id }));
            return (
              <div
                key={block.id}
                className="rounded-3xl bg-koraku-panel p-5 ring-1 ring-neutral-200/60"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="text-sm font-bold text-neutral-700">
                      {title}
                    </h2>
                    <p className="mt-1 text-xs font-medium text-koraku-muted">
                      {block.configured
                        ? `Default: ${block.default_model}`
                        : "Not configured — add API keys in .env and restart the API"}
                    </p>
                  </div>
                  <span
                    className={
                      block.configured
                        ? "rounded-full bg-emerald-100 px-2.5 py-1 text-[11px] font-bold text-emerald-800"
                        : "rounded-full bg-neutral-200 px-2.5 py-1 text-[11px] font-bold text-neutral-600"
                    }
                  >
                    {block.configured ? "Ready" : "Off"}
                  </span>
                </div>
                <ul className="mt-4 space-y-1 rounded-2xl bg-white p-2 ring-1 ring-neutral-200/80">
                  {rows.map((row) => (
                    <li
                      key={`${block.id}-${row.id}`}
                      className="rounded-xl px-3 py-2.5 text-sm font-semibold text-koraku-ink"
                    >
                      {(row.label || row.id).trim()}
                      {row.id === block.default_model ? (
                        <span className="ml-2 text-xs font-medium text-koraku-muted">
                          default
                        </span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </section>

        <section className="mt-10 rounded-3xl bg-koraku-panel p-5">
          <h2 className="text-sm font-bold text-neutral-600">Configure</h2>
          <p className="mt-2 text-sm font-medium leading-relaxed text-koraku-muted">
            Set <code className="font-mono">FIREWORKS_API_KEY</code>,{" "}
            <code className="font-mono">LLM_OPENAI_COMPAT_IDS</code>, or{" "}
            <code className="font-mono">ANTHROPIC_API_KEY</code> in the repo-root{" "}
            <code className="font-mono">.env</code>, then restart{" "}
            <code className="font-mono">python main.py</code>.
          </p>
          <Link
            href="https://github.com/meet447/koraku/blob/main/docs/SELF_HOST.md"
            className="mt-4 inline-block text-sm font-semibold text-koraku-ink underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            Self-host guide
          </Link>
        </section>
      </div>
    </main>
  );
}
