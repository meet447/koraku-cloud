import Link from "next/link";
import { LANDING_CONTAINER, LANDING_MUTED_SURFACE, LANDING_SECTION } from "@/components/landing/landing-layout";
import { APP_BASE } from "@/lib/app-path";

export function FinalCtaSection() {
  return (
    <section className={`border-b border-black/10 ${LANDING_MUTED_SURFACE} ${LANDING_SECTION}`}>
      <div className={`${LANDING_CONTAINER} text-center`}>
        <h2 className="landing-pixel-headline text-[3rem] font-semibold leading-[0.92] tracking-[-0.06em] text-[#282522] sm:text-[4.2rem]">
          Start automating in minutes
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-base font-medium leading-7 text-stone-500 sm:text-[17px]">
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
            className="inline-flex h-12 items-center justify-center rounded-md border border-black/15 bg-white px-6 text-sm font-semibold text-stone-800 shadow-[4px_4px_0_rgba(0,0,0,0.04)] transition hover:-translate-y-0.5"
          >
            Open app
          </Link>
        </div>
      </div>
    </section>
  );
}
