"use client";

import { useState } from "react";
import clsx from "clsx";
import { ChevronDown, ChevronUp, X } from "lucide-react";

export type QueuedMessagePreview = { id: string; text: string };

export function MessageQueueBar({
  items,
  onRemove,
}: {
  items: QueuedMessagePreview[];
  onRemove: (id: string) => void;
}) {
  const [open, setOpen] = useState(true);
  if (!items.length) return null;

  const n = items.length;
  const label = n === 1 ? "1 message queued" : `${n} messages queued`;

  return (
    <div className="pointer-events-auto mx-auto mb-2 w-full min-w-0 max-w-3xl px-4">
      <div className="overflow-hidden rounded-2xl border border-neutral-200/90 bg-white shadow-sm">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="flex w-full items-center justify-between gap-2 px-3 py-2.5 text-left text-sm font-semibold text-koraku-ink hover:bg-neutral-50/80"
        >
          <span>{label}</span>
          {open ? (
            <ChevronUp className="h-4 w-4 shrink-0 text-neutral-500" aria-hidden />
          ) : (
            <ChevronDown className="h-4 w-4 shrink-0 text-neutral-500" aria-hidden />
          )}
        </button>
        <div
          className={clsx(
            "border-t border-neutral-100 px-3 py-2",
            open ? "block" : "hidden",
          )}
        >
          <ol className="space-y-2">
            {items.map((it, idx) => (
              <li
                key={it.id}
                className="flex items-start gap-2 text-[13px] leading-snug text-neutral-700"
              >
                <span className="mt-0.5 w-5 shrink-0 font-mono text-[11px] text-neutral-400">
                  {idx + 1}.
                </span>
                <span className="min-w-0 flex-1 whitespace-pre-wrap break-words">
                  {it.text || "·"}
                </span>
                <button
                  type="button"
                  onClick={() => onRemove(it.id)}
                  className="shrink-0 rounded-full p-1 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700"
                  aria-label="Remove from queue"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </div>
  );
}
