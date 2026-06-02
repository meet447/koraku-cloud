"use client";

import { useEffect, useState } from "react";
import type { KorakuHealth } from "@/lib/koraku-health";
import { fetchKorakuHealth } from "@/lib/koraku-health";

export type { KorakuHealth };

export function useKorakuHealth() {
  const [health, setHealth] = useState<KorakuHealth | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void fetchKorakuHealth().then((data) => {
      if (cancelled) return;
      setHealth(data);
      setError(!data);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return { health, error };
}
