import { CalendarClock, History, ShieldCheck } from "lucide-react";
import { automationCards } from "@/components/landing/landing-data";
import { LANDING_CONTAINER, LANDING_PAGE_BG, LANDING_SECTION, LANDING_SURFACE } from "@/components/landing/landing-layout";

const icons = [CalendarClock, ShieldCheck, History] as const;

export function AutomationsSection() {
  return (
    <section id="automations" className={`scroll-mt-24 border-b border-black/10 ${LANDING_PAGE_BG} ${LANDING_SECTION}`}>
      <div className={LANDING_CONTAINER}>
        <p className="mb-4 inline-block rounded bg-white px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-stone-500 shadow-sm">
          Automations
        </p>
        <h2 className="landing-pixel-headline max-w-4xl text-[3.2rem] font-semibold leading-[0.95] tracking-[-0.055em] text-[#282522] sm:text-[4.8rem]">
          Put recurring work on autopilot
        </h2>
        <p className="mt-4 max-w-2xl text-base font-medium leading-7 text-stone-500 sm:text-[17px]">
          Scheduled automations run in the background with the same memory, connections, and approval
          rules as chat — so nothing slips through without you.
        </p>

        <div className="mt-10 grid gap-5 md:grid-cols-3">
          {automationCards.map((card, index) => {
            const Icon = icons[index] ?? CalendarClock;
            return (
              <article
                key={card.title}
                className={`rounded-lg border border-black/10 ${LANDING_SURFACE} p-6 shadow-[10px_10px_0_rgba(0,0,0,0.04)]`}
              >
                <span className="flex h-11 w-11 items-center justify-center rounded-md border border-orange-200 bg-orange-50 text-orange-700">
                  <Icon className="h-5 w-5" strokeWidth={1.75} aria-hidden />
                </span>
                <h3 className="mt-5 text-lg font-semibold text-stone-900">{card.title}</h3>
                <p className="mt-2 text-[15px] leading-relaxed text-stone-500">{card.description}</p>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
