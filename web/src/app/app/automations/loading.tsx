import { AutomationsPageSkeleton } from "@/components/AutomationsSkeleton";

export default function AutomationsLoading() {
  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col">
      <header className="flex shrink-0 items-center justify-between border-b border-neutral-200/50 bg-white px-6 py-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.22em] text-orange-700">Habits</p>
          <h1 className="mt-1 text-xl font-bold tracking-tight text-koraku-ink">Background work</h1>
        </div>
      </header>
      <AutomationsPageSkeleton />
    </div>
  );
}
