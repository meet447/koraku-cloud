"use client";

import clsx from "clsx";

/** Placeholder while the assistant turn is open but no prose has streamed yet. */
export function StreamingReplySkeleton({ className }: { className?: string }) {
  return (
    <div
      className={clsx("mb-3 space-y-2.5 pl-0.5", className)}
      aria-hidden
      role="presentation"
    >
      <div className="koraku-shimmer h-3.5 w-[92%] max-w-xl rounded-md" />
      <div className="koraku-shimmer h-3.5 w-[72%] max-w-lg rounded-md [animation-delay:120ms]" />
      <div className="koraku-shimmer h-3.5 w-[48%] max-w-md rounded-md [animation-delay:240ms]" />
    </div>
  );
}
