export function ChatMessagesSkeleton() {
  const line = (w: string, delay?: string) => (
    <div
      className={`koraku-shimmer h-3.5 rounded-md ${w}${delay ? ` ${delay}` : ""}`}
    />
  );
  const block = (key: string) => (
    <div key={key} className="mb-10 space-y-4">
      <div className="flex justify-end">
        <div className="koraku-shimmer h-11 w-[min(72%,18rem)] rounded-3xl" />
      </div>
      <div className="space-y-2.5 pl-1">
        {line("w-[78%] max-w-xl")}
        {line("w-[58%] max-w-md", "[animation-delay:120ms]")}
        <div className="koraku-shimmer mt-3 h-28 w-full max-w-2xl rounded-2xl [animation-delay:200ms]" />
      </div>
    </div>
  );
  return (
    <div className="space-y-2" aria-busy aria-label="Loading conversation">
      {block("a")}
      {block("b")}
    </div>
  );
}
