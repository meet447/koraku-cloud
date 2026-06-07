type IntegrationsSkeletonProps = {
  count?: number;
};

function IntegrationCardSkeleton({ index }: { index: number }) {
  const delay = index % 3 === 1 ? "[animation-delay:120ms]" : index % 3 === 2 ? "[animation-delay:240ms]" : "";

  return (
    <li
      className="flex flex-col overflow-hidden rounded-2xl border border-neutral-200/90 bg-white shadow-[0_1px_3px_rgb(0_0_0_/0.04)]"
      aria-hidden
    >
      <div className="flex items-center gap-3 px-4 pb-3 pt-4">
        <div className={`koraku-shimmer h-11 w-11 shrink-0 rounded-xl ${delay}`} />
        <div className={`koraku-shimmer h-5 w-32 rounded-md ${delay}`} />
      </div>
      <div className="mt-auto flex min-h-[4.5rem] items-stretch justify-between gap-3 bg-neutral-100 px-4 py-3">
        <div className="min-w-0 flex-1 space-y-2 py-1">
          <div className={`koraku-shimmer h-3.5 w-full rounded-md ${delay}`} />
          <div className={`koraku-shimmer h-3.5 w-[88%] rounded-md ${delay}`} />
          <div className={`koraku-shimmer h-3.5 w-[62%] rounded-md ${delay}`} />
        </div>
        <div className={`koraku-shimmer h-4 w-14 shrink-0 self-center rounded-md ${delay}`} />
      </div>
    </li>
  );
}

export function IntegrationsSkeleton({ count = 6 }: IntegrationsSkeletonProps) {
  return (
    <ul
      className="mt-8 grid gap-5 sm:grid-cols-2"
      aria-busy="true"
      aria-label="Loading integrations"
    >
      {Array.from({ length: count }, (_, index) => (
        <IntegrationCardSkeleton key={`integration-skeleton-${index}`} index={index} />
      ))}
    </ul>
  );
}
