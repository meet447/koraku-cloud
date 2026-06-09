"use client";

import clsx from "clsx";
import { BrandMark } from "@/components/BrandMark";

export function KorakuAppLoading({
  className,
  label = "Loading Koraku",
}: {
  className?: string;
  label?: string;
}) {
  return (
    <div
      className={clsx(
        "flex h-[100dvh] w-full flex-col items-center justify-center bg-white text-koraku-ink",
        className,
      )}
      role="status"
      aria-busy="true"
      aria-live="polite"
      aria-label={label}
    >
      <div className="flex flex-col items-center gap-5">
        <div className="koraku-app-loading-mark relative flex h-[4.5rem] w-[4.5rem] items-center justify-center">
          <span className="koraku-app-loading-ring absolute inset-0 rounded-full" aria-hidden />
          <BrandMark size={48} priority />
        </div>
        <div className="flex items-center gap-1.5" aria-hidden>
          <span className="koraku-app-loading-dot h-1.5 w-1.5 rounded-full bg-orange-500" />
          <span className="koraku-app-loading-dot koraku-app-loading-dot-delay-1 h-1.5 w-1.5 rounded-full bg-orange-500" />
          <span className="koraku-app-loading-dot koraku-app-loading-dot-delay-2 h-1.5 w-1.5 rounded-full bg-orange-500" />
        </div>
      </div>
      <span className="sr-only">{label}</span>
    </div>
  );
}
