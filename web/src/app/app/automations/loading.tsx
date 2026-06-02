export default function AutomationsLoading() {
  return (
    <div className="flex min-h-0 min-w-0 flex-1 animate-pulse flex-col">
      <header className="flex shrink-0 items-center justify-between border-b border-neutral-200/50 bg-white px-6 py-4">
        <div>
          <div className="h-3 w-24 rounded bg-neutral-200" />
          <div className="mt-2 h-6 w-40 rounded bg-neutral-200" />
        </div>
        <div className="flex gap-2">
          <div className="h-9 w-24 rounded-full bg-neutral-100" />
          <div className="h-9 w-20 rounded-full bg-neutral-200" />
        </div>
      </header>
      <div className="flex min-h-0 flex-1">
        <aside className="w-full max-w-sm shrink-0 border-r border-neutral-200/80 bg-neutral-50/50 p-3">
          <div className="h-10 rounded-xl bg-neutral-100" />
          <ul className="mt-4 space-y-2">
            {[1, 2, 3, 4].map((i) => (
              <li key={i} className="h-24 rounded-2xl bg-neutral-100" />
            ))}
          </ul>
        </aside>
        <section className="min-h-0 flex-1 bg-white px-6 py-6">
          <div className="h-6 w-48 rounded bg-neutral-200" />
          <div className="mt-3 h-4 w-64 rounded bg-neutral-100" />
          <div className="mt-6 h-24 rounded-2xl bg-neutral-50" />
        </section>
      </div>
    </div>
  );
}
