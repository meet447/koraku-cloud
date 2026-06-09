type DelayClass = "" | "[animation-delay:120ms]" | "[animation-delay:240ms]";

function delayClass(index: number): DelayClass {
  if (index % 3 === 1) return "[animation-delay:120ms]";
  if (index % 3 === 2) return "[animation-delay:240ms]";
  return "";
}

function Shimmer({ className }: { className: string }) {
  return <div className={`koraku-shimmer ${className}`} aria-hidden />;
}

export function OnboardingWizardSkeleton({ stepCount = 6 }: { stepCount?: number }) {
  return (
    <div aria-busy="true" aria-label="Loading onboarding">
      <div className="mb-10">
        <Shimmer className="h-3 w-24 rounded-md" />
        <div className="mt-5 flex flex-wrap items-end justify-between gap-4">
          <div className="space-y-2">
            <Shimmer className="h-4 w-28 rounded-md" />
            <Shimmer className="h-9 w-full max-w-md rounded-lg [animation-delay:120ms]" />
          </div>
          <Shimmer className="h-4 w-36 rounded-md [animation-delay:240ms]" />
        </div>
        <div className="mt-5 flex gap-2">
          {Array.from({ length: stepCount }, (_, index) => (
            <Shimmer
              key={`onboarding-progress-skeleton-${index}`}
              className={`h-2 flex-1 rounded-full ${delayClass(index)}`}
            />
          ))}
        </div>
      </div>

      <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-neutral-200/80 sm:p-8">
        <Shimmer className="h-8 w-[min(100%,28rem)] rounded-lg" />
        <Shimmer className="mt-3 h-4 w-full max-w-2xl rounded-md [animation-delay:120ms]" />
        <Shimmer className="mt-2 h-4 w-[82%] max-w-xl rounded-md [animation-delay:240ms]" />
        <div className="mt-8 space-y-5">
          <Shimmer className="h-4 w-32 rounded-md" />
          <Shimmer className="h-12 w-full rounded-xl" />
          <Shimmer className="h-32 w-full rounded-xl [animation-delay:120ms]" />
          <div className="flex flex-wrap gap-2 pt-2">
            {Array.from({ length: 4 }, (_, index) => (
              <Shimmer
                key={`onboarding-chip-skeleton-${index}`}
                className={`h-9 w-28 rounded-full ${delayClass(index)}`}
              />
            ))}
          </div>
        </div>
      </div>

      <div className="mt-8 flex flex-wrap items-center justify-between gap-3">
        <Shimmer className="h-11 w-24 rounded-full" />
        <div className="flex gap-3">
          <Shimmer className="h-11 w-28 rounded-full [animation-delay:120ms]" />
          <Shimmer className="h-11 w-24 rounded-full [animation-delay:240ms]" />
        </div>
      </div>
    </div>
  );
}

export function OnboardingConnectionsSkeleton({ count = 4 }: { count?: number }) {
  return (
    <ul
      className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3"
      aria-busy="true"
      aria-label="Loading integrations"
    >
      {Array.from({ length: count }, (_, index) => {
        const delay = delayClass(index);
        return (
          <li
            key={`onboarding-connection-skeleton-${index}`}
            className="flex items-center gap-3 rounded-2xl border border-neutral-200/90 bg-koraku-panel px-4 py-3"
            aria-hidden
          >
            <Shimmer className={`h-10 w-10 shrink-0 rounded-xl ${delay}`} />
            <div className="min-w-0 flex-1 space-y-2">
              <Shimmer className={`h-4 w-28 rounded-md ${delay}`} />
              <Shimmer className={`h-3 w-full rounded-md ${delay}`} />
              <Shimmer className={`h-3 w-[70%] rounded-md ${delay}`} />
            </div>
            <Shimmer className={`h-8 w-20 shrink-0 rounded-full ${delay}`} />
          </li>
        );
      })}
    </ul>
  );
}

export function OnboardingAboutEnrichSkeleton() {
  return (
    <div
      className="space-y-3 rounded-xl border border-neutral-200/80 bg-white/90 p-4"
      aria-busy="true"
      aria-label="Building profile from links"
    >
      <Shimmer className="h-3.5 w-40 rounded-md" />
      <Shimmer className="h-3.5 w-full rounded-md [animation-delay:120ms]" />
      <Shimmer className="h-3.5 w-[94%] rounded-md [animation-delay:240ms]" />
      <Shimmer className="h-3.5 w-[88%] rounded-md" />
      <Shimmer className="h-3.5 w-[72%] rounded-md [animation-delay:120ms]" />
    </div>
  );
}
