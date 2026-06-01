"use client";

import Link from "next/link";
import { useKorakuHealth } from "@/hooks/useKorakuHealth";

export function SetupStatusBanner() {
  const { health, error } = useKorakuHealth();

  if (error) {
    return (
      <div
        role="status"
        className="border-b border-amber-200 bg-amber-50 px-4 py-3 text-center text-sm font-medium text-amber-950"
      >
        Cannot reach the Koraku API. Start the Python backend or check{" "}
        <code className="rounded bg-amber-100/80 px-1">KORAKU_BACKEND_URL</code>.
      </div>
    );
  }

  if (!health || health.llmConfigured) return null;

  return (
    <div
      role="status"
      className="border-b border-orange-200 bg-orange-50 px-4 py-3 text-center text-sm font-medium leading-relaxed text-orange-950"
    >
      No language model is configured yet. Add{" "}
      <code className="rounded bg-orange-100/80 px-1">FIREWORKS_API_KEY</code> or an OpenAI-compatible
      provider in <code className="rounded bg-orange-100/80 px-1">.env</code>, then restart the API.{" "}
      <Link
        href="https://github.com/meet447/koraku/blob/main/docs/SELF_HOST.md"
        className="font-semibold underline"
        target="_blank"
        rel="noopener noreferrer"
      >
        Self-host guide
      </Link>
    </div>
  );
}
