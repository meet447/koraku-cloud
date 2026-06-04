"use client";

import { Clock, Cloud } from "lucide-react";
import { useLocalContext } from "@/hooks/useLocalContext";

const iconClass = "h-3.5 w-3.5 shrink-0 text-neutral-400";

export function NewChatLocalContext() {
  const { time, place } = useLocalContext();

  return (
    <p className="mb-4 flex flex-wrap items-center justify-center gap-x-1.5 gap-y-1 text-sm font-medium tracking-tight text-koraku-muted">
      <span className="inline-flex items-center gap-1">
        <Clock className={iconClass} strokeWidth={2} aria-hidden />
        <span>{time}</span>
      </span>
      {place ? (
        <>
          <span aria-hidden className="text-neutral-300">
            ·
          </span>
          <span>{place.city}</span>
          {place.temperatureC != null ? (
            <>
              <span aria-hidden className="text-neutral-300">
                ·
              </span>
              <span className="inline-flex items-center gap-1">
                <Cloud className={iconClass} strokeWidth={2} aria-hidden />
                <span>{place.temperatureC}°</span>
              </span>
            </>
          ) : null}
        </>
      ) : null}
    </p>
  );
}
