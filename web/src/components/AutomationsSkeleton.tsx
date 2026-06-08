type DelayClass = "" | "[animation-delay:120ms]" | "[animation-delay:240ms]";

function delayClass(index: number): DelayClass {
  if (index % 3 === 1) return "[animation-delay:120ms]";
  if (index % 3 === 2) return "[animation-delay:240ms]";
  return "";
}

function Shimmer({ className }: { className: string }) {
  return <div className={`koraku-shimmer ${className}`} aria-hidden />;
}

export function AutomationsListSkeleton({ count = 4 }: { count?: number }) {
  return (
    <ul className="space-y-1" aria-busy="true" aria-label="Loading automations">
      {Array.from({ length: count }, (_, index) => {
        const delay = delayClass(index);
        return (
          <li
            key={`automation-list-skeleton-${index}`}
            className="rounded-2xl px-3 py-3 ring-1 ring-neutral-200/60"
            aria-hidden
          >
            <div className="flex items-center gap-2">
              <Shimmer className={`h-6 w-6 shrink-0 rounded-md ${delay}`} />
              <Shimmer className={`h-4 flex-1 rounded-md ${delay}`} />
            </div>
            <Shimmer className={`mt-2 h-3 w-16 rounded-md ${delay}`} />
            <Shimmer className={`mt-2 h-3 w-full rounded-md ${delay}`} />
            <Shimmer className={`mt-1.5 h-3 w-[88%] rounded-md ${delay}`} />
          </li>
        );
      })}
    </ul>
  );
}

export function AutomationsDetailSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading automation details">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <Shimmer className="h-6 w-48 max-w-full rounded-md" />
            <Shimmer className="h-5 w-16 rounded-full" />
          </div>
          <Shimmer className="h-4 w-64 max-w-full rounded-md [animation-delay:120ms]" />
          <Shimmer className="h-3 w-40 rounded-md [animation-delay:240ms]" />
        </div>
        <div className="flex shrink-0 gap-2">
          <Shimmer className="h-9 w-24 rounded-full" />
          <Shimmer className="h-9 w-24 rounded-full [animation-delay:120ms]" />
          <Shimmer className="h-9 w-9 rounded-full [animation-delay:240ms]" />
        </div>
      </div>
      <Shimmer className="mt-6 h-24 w-full rounded-2xl" />
      <Shimmer className="mt-8 h-4 w-28 rounded-md" />
      <AutomationsRunHistorySkeleton />
    </div>
  );
}

export function AutomationsRunHistorySkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="mt-4 space-y-4" aria-busy="true" aria-label="Loading run history">
      <Shimmer className="h-3 w-36 rounded-md" />
      {Array.from({ length: count }, (_, index) => {
        const delay = delayClass(index);
        return (
          <div
            key={`automation-run-skeleton-${index}`}
            className="rounded-2xl border border-neutral-200/80 px-4 py-3"
            aria-hidden
          >
            <div className="flex items-center gap-2">
              <Shimmer className={`h-4 w-40 rounded-md ${delay}`} />
              <Shimmer className={`h-4 w-14 rounded-full ${delay}`} />
            </div>
            <Shimmer className={`mt-2 h-3 w-full rounded-md ${delay}`} />
            <Shimmer className={`mt-1.5 h-3 w-[72%] rounded-md ${delay}`} />
          </div>
        );
      })}
    </div>
  );
}

export function AutomationsPageSkeleton() {
  return (
    <div className="flex min-h-0 flex-1">
      <aside className="flex w-full max-w-sm shrink-0 flex-col border-r border-neutral-200/80 bg-neutral-50/50">
        <div className="p-3">
          <Shimmer className="h-10 w-full rounded-xl" />
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-4">
          <AutomationsListSkeleton />
        </div>
      </aside>
      <section className="min-h-0 min-w-0 flex-1 overflow-y-auto bg-white px-4 py-6 md:px-6">
        <AutomationsDetailSkeleton />
      </section>
    </div>
  );
}
