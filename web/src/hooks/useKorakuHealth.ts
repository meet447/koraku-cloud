"use client";

import { useEffect, useState } from "react";

export type KorakuHealth = {
  llmConfigured: boolean;
  mode: string;
  llmProvider: string;
};

export function useKorakuHealth() {
  const [health, setHealth] = useState<KorakuHealth | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch("/koraku-api/health", { cache: "no-store" });
        if (!r.ok) throw new Error(String(r.status));
        const data = (await r.json()) as Record<string, unknown>;
        if (cancelled) return;
        setHealth({
          llmConfigured: Boolean(data.llm_configured),
          mode: String(data.mode ?? "unknown"),
          llmProvider: String(data.llm_provider ?? ""),
        });
        setError(false);
      } catch {
        if (!cancelled) {
          setHealth(null);
          setError(true);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return { health, error };
}
