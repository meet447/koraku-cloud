"use client";

import { useKorakuHealth } from "@/hooks/useKorakuHealth";
import { KORAKU_COPY } from "@/lib/korakuBrand";

export function SetupStatusBanner() {
  const { health, error } = useKorakuHealth();

  if (error) {
    return (
      <div
        role="status"
        className="border-b border-amber-200 bg-amber-50 px-4 py-3 text-center text-sm font-medium text-amber-950"
      >
        Cannot reach Koraku right now. Please try again in a moment.
      </div>
    );
  }

  if (!health || health.llmConfigured) return null;

  return (
    <div
      role="status"
      className="border-b border-orange-200 bg-orange-50 px-4 py-3 text-center text-sm font-medium leading-relaxed text-orange-950"
    >
      {KORAKU_COPY.setupLlm}
    </div>
  );
}
