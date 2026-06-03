import { howItWorksSteps } from "@/components/landing/landing-data";
import { LANDING_CONTAINER, LANDING_PAGE_BG, LANDING_SECTION, LANDING_SURFACE } from "@/components/landing/landing-layout";

export function HowItWorksSection() {
  return (
    <section id="how-it-works" className={`scroll-mt-24 border-b border-black/10 ${LANDING_PAGE_BG} ${LANDING_SECTION}`}>
      <div className={LANDING_CONTAINER}>
        <p className="mb-4 inline-block rounded bg-white px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-stone-500 shadow-sm">
          How it works
        </p>
        <h2 className="landing-pixel-headline max-w-4xl text-[3.2rem] font-semibold leading-[0.95] tracking-[-0.055em] text-[#282522] sm:text-[4.8rem]">
          From prompt to finished work
        </h2>
        <p className="mt-4 max-w-2xl text-base font-medium leading-7 text-stone-500 sm:text-[17px]">
          Koraku is a hosted AI workspace — connect your apps, instruct agents in plain language, and
          review results before anything goes out.
        </p>

        <div className="mt-10 grid gap-5 md:grid-cols-3">
          {howItWorksSteps.map((item) => (
            <article
              key={item.step}
              className={`rounded-lg border border-black/10 ${LANDING_SURFACE} p-6 shadow-[10px_10px_0_rgba(0,0,0,0.04)]`}
            >
              <p className="font-mono text-xs font-semibold uppercase tracking-[0.2em] text-orange-700">
                {item.step}
              </p>
              <h3 className="mt-4 text-xl font-semibold tracking-tight text-stone-900">{item.title}</h3>
              <p className="mt-3 text-[15px] leading-relaxed text-stone-500">{item.description}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
