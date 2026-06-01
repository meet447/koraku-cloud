"use client";

import { useEffect, useRef, useState } from "react";
import {
  AGENT_BUSY_PHRASES,
  formatElapsedClock,
} from "@/lib/agentBusyPhrases";

function useElapsedSince(startedAtMs: number): number {
  const [ms, setMs] = useState(() => Date.now() - startedAtMs);

  useEffect(() => {
    const tick = () => setMs(Date.now() - startedAtMs);
    tick();
    const id = window.setInterval(tick, 100);
    const onVis = () => {
      if (document.visibilityState === "visible") tick();
    };
    document.addEventListener("visibilitychange", onVis);
    return () => {
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, [startedAtMs]);

  return ms;
}

function useRotatingPhrase(): string {
  const offsetRef = useRef(
    Math.floor(Math.random() * AGENT_BUSY_PHRASES.length),
  );
  const [i, setI] = useState(0);

  useEffect(() => {
    offsetRef.current = Math.floor(Math.random() * AGENT_BUSY_PHRASES.length);
    setI(0);
    const id = window.setInterval(() => setI((n) => n + 1), 3800);
    return () => clearInterval(id);
  }, []);

  const idx = (offsetRef.current + i) % AGENT_BUSY_PHRASES.length;
  return AGENT_BUSY_PHRASES[idx] ?? AGENT_BUSY_PHRASES[0];
}

/** Shown while the assistant stream is active for the current turn. */
export function AgentBusyRow({ startedAtMs }: { startedAtMs: number }) {
  const elapsed = useElapsedSince(startedAtMs);
  const phrase = useRotatingPhrase();

  return (
    <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm font-medium text-neutral-500">
      <span className="inline-flex items-center gap-2">
        <span
          className="inline-flex h-2 w-2 shrink-0 animate-pulse rounded-full bg-koraku-accent"
          aria-hidden
        />
        <span className="text-neutral-600">{phrase}…</span>
      </span>
      <span
        className="font-mono text-xs font-semibold tabular-nums text-neutral-400"
        aria-label={`Elapsed ${formatElapsedClock(elapsed)}`}
      >
        {formatElapsedClock(elapsed)}
      </span>
    </div>
  );
}
