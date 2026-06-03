import { useCases } from "@/components/landing/landing-data";
import { LANDING_CONTAINER, LANDING_PAGE_BG, LANDING_SECTION } from "@/components/landing/landing-layout";

export function UseCasesSection() {
  return (
    <section id="use-cases" className={`scroll-mt-24 border-b border-black/10 ${LANDING_PAGE_BG} ${LANDING_SECTION}`}>
      <div className={LANDING_CONTAINER}>
        <p className="mb-4 inline-block rounded bg-white px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-stone-500 shadow-sm">
          Use cases
        </p>
        <h2 className="landing-pixel-headline max-w-4xl text-[3.2rem] font-semibold leading-[0.95] tracking-[-0.055em] text-[#282522] sm:text-[4.8rem]">
          Workflows teams run every day
        </h2>
        <p className="mt-4 max-w-2xl text-base font-medium leading-7 text-stone-500 sm:text-[17px]">
          Same agents in chat, on a schedule, or from your phone — tuned to how you actually operate.
        </p>

        <div className="mt-10 grid gap-5 sm:grid-cols-2">
          {useCases.map((item) => (
            <article
              key={item.title}
              className={`rounded-lg border border-black/10 bg-white p-6 shadow-[10px_10px_0_rgba(0,0,0,0.03)]`}
            >
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-stone-400">{item.tag}</p>
              <h3 className="mt-2 text-2xl font-semibold tracking-tight text-stone-900">{item.title}</h3>
              <p className="mt-3 text-[15px] leading-relaxed text-stone-600">{item.outcome}</p>
              <ul className="mt-4 space-y-2 border-t border-black/10 pt-4">
                {item.bullets.map((bullet) => (
                  <li key={bullet} className="flex gap-2 text-sm leading-relaxed text-stone-500">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-orange-500" aria-hidden />
                    {bullet}
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
