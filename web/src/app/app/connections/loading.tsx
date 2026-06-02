export default function ConnectionsLoading() {
  return (
    <main className="min-h-0 flex-1 overflow-y-auto bg-white px-6 py-10">
      <div className="mx-auto max-w-5xl animate-pulse">
        <div className="h-3 w-24 rounded bg-neutral-200" />
        <div className="mt-3 h-10 w-64 max-w-full rounded-lg bg-neutral-200" />
        <div className="mt-3 h-4 w-full max-w-xl rounded bg-neutral-100" />
        <div className="mt-8 h-12 w-full rounded-full bg-neutral-100" />
        <div className="mt-5 flex gap-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-9 w-20 rounded-full bg-neutral-100" />
          ))}
        </div>
        <ul className="mt-8 grid gap-5 sm:grid-cols-2">
          {[1, 2, 3, 4].map((i) => (
            <li
              key={i}
              className="h-44 rounded-2xl border border-neutral-200/90 bg-white"
            />
          ))}
        </ul>
      </div>
    </main>
  );
}
