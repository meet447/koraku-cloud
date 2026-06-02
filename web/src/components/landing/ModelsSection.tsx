import { Cpu } from "lucide-react";
import { modelCards } from "@/components/landing/landing-data";
import { cn } from "@/lib/cn";

export function ModelsSection() {
  return (
    <section id="models" className="bg-[#f8f8f7] px-5 py-28 sm:px-8">
      <div className="mx-auto max-w-[1100px]">
        <div className="max-w-2xl">
          <div className="mb-8 flex h-14 w-14 items-center justify-center rounded-md border border-black/10 bg-white shadow-[6px_6px_0_rgba(0,0,0,0.05)]">
            <Cpu className="h-6 w-6 text-orange-700" />
          </div>
          <h2 className="landing-pixel-headline font-landing-serif text-4xl font-semibold leading-[0.95] tracking-[-0.06em] text-[#282522] sm:text-5xl">
            Route each task to the model that fits
          </h2>
          <p className="mt-5 text-sm leading-7 text-stone-600">
            Use fast models for summaries, advanced models for deep reasoning, hosted defaults
            for everyday work, or custom providers when you need full control.
          </p>
        </div>

        <div className="mt-12 grid gap-4 md:grid-cols-4">
          {modelCards.map((model) => (
            <article
              key={model.name}
              className="rounded-lg border border-black/10 bg-white p-4 shadow-[8px_8px_0_rgba(0,0,0,0.04)]"
            >
              <div className={cn("mb-8 inline-flex rounded px-2 py-1 font-mono text-[10px]", model.color)}>
                {model.badge}
              </div>
              <h3 className="text-xl font-semibold tracking-tight text-stone-900">{model.name}</h3>
              <p className="mt-3 text-sm leading-6 text-stone-500">{model.description}</p>
              <div className="mt-6 grid grid-cols-8 gap-1">
                {Array.from({ length: 24 }).map((_, index) => (
                  <span
                    key={index}
                    className={cn(
                      "h-2 rounded-[1px]",
                      index % 5 === 0 ? "bg-orange-300" : "bg-stone-200",
                    )}
                  />
                ))}
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
