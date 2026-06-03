import Link from "next/link";
import { trustPoints } from "@/components/landing/landing-data";
import { LANDING_CONTAINER, LANDING_PAGE_BG, LANDING_SECTION, LANDING_SURFACE } from "@/components/landing/landing-layout";

export function TrustSection() {
  return (
    <section id="trust" className={`scroll-mt-24 border-b border-black/10 ${LANDING_PAGE_BG} ${LANDING_SECTION}`}>
      <div className={LANDING_CONTAINER}>
        <p className="mb-4 inline-block rounded bg-white px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-stone-500 shadow-sm">
          Trust
        </p>
        <h2 className="landing-pixel-headline max-w-4xl text-[3.2rem] font-semibold leading-[0.95] tracking-[-0.055em] text-[#282522] sm:text-[4.8rem]">
          Built for work you can trust
        </h2>
        <p className="mt-4 max-w-2xl text-base font-medium leading-7 text-stone-500 sm:text-[17px]">
          Koraku is designed for real workflows — confirm before high-impact actions and keep control
          of what stays in your account.
        </p>

        <div className="mt-10 grid gap-5 sm:grid-cols-2">
          {trustPoints.map((point) => (
            <article
              key={point.title}
              className={`rounded-lg border border-black/10 ${LANDING_SURFACE} p-6 shadow-[10px_10px_0_rgba(0,0,0,0.04)]`}
            >
              <h3 className="text-lg font-semibold text-stone-900">{point.title}</h3>
              <p className="mt-2 text-[15px] leading-relaxed text-stone-500">
                {point.title === "Clear policies" ? (
                  <>
                    See our{" "}
                    <Link href="/privacy" className="font-semibold text-stone-700 underline-offset-2 hover:underline">
                      Privacy Policy
                    </Link>
                    ,{" "}
                    <Link href="/security" className="font-semibold text-stone-700 underline-offset-2 hover:underline">
                      Security
                    </Link>
                    , and{" "}
                    <Link href="/terms" className="font-semibold text-stone-700 underline-offset-2 hover:underline">
                      Terms
                    </Link>
                    .
                  </>
                ) : (
                  point.description
                )}
              </p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
