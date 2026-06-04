"use client";

import { useLocalContext } from "@/hooks/useLocalContext";

export function NewChatLocalContext() {
  const { time, place } = useLocalContext();

  return (
    <p className="mb-4 text-sm font-medium tracking-tight text-koraku-muted">
      <span>{time}</span>
      {place ? (
        <>
          <span aria-hidden className="mx-1.5 text-neutral-300">
            ·
          </span>
          <span>
            {place.city}
            {place.temperatureC != null ? ` ${place.temperatureC}°` : null}
          </span>
        </>
      ) : null}
    </p>
  );
}
