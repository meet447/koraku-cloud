import Link from "next/link";
import { LANDING_CONTAINER, LANDING_SECTION } from "@/components/landing/landing-layout";
import { APP_BASE } from "@/lib/app-path";

export function FinalCtaSection() {
  return (
    <section className={`relative overflow-hidden border-b border-black/10 ${LANDING_SECTION}`}>
      <div
        className="pointer-events-none absolute inset-0 bg-[url('/footer.png')] bg-cover bg-center bg-no-repeat"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute inset-0 bg-gradient-to-b from-[#fcfcfb]/95 via-[#fcfcfb]/80 to-[#fcfcfb]/50"
        aria-hidden
      />

      <div className={`relative z-10 ${LANDING_CONTAINER} py-20 text-center sm:py-24 lg:py-28`}>
        <h2 className="landing-pixel-headline text-[3rem] font-semibold leading-[0.92] tracking-[-0.06em] text-[#282522] drop-shadow-[0_1px_0_rgba(252,252,251,0.9)] sm:text-[4.2rem]">
          Start automating in minutes
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-base font-medium leading-7 text-stone-600 sm:text-[17px]">
          Sign in with Google or GitHub, connect your apps, and send your first instruction — your
          workspace is ready in the cloud.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
          <Link
            href="/sign-in"
            className="inline-flex h-12 items-center justify-center rounded-md bg-[#171717] px-6 text-sm font-semibold text-white shadow-[0_8px_18px_rgba(0,0,0,0.2)] transition hover:-translate-y-0.5"
          >
            Start free
          </Link>
          <Link
            href={APP_BASE}
            className="inline-flex h-12 items-center justify-center rounded-md border border-black/15 bg-white/95 px-6 text-sm font-semibold text-stone-800 shadow-[4px_4px_0_rgba(0,0,0,0.04)] backdrop-blur-sm transition hover:-translate-y-0.5"
          >
            Open app
          </Link>
        </div>
      </div>
    </section>
  );
}
