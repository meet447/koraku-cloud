import Link from "next/link";
import { LANDING_CONTAINER } from "@/components/landing/landing-layout";
import { APP_BASE } from "@/lib/app-path";

export function TopNav() {
  return (
    <header className="sticky top-0 z-50 border-b border-black/10 bg-[#f8f8f7]/90 backdrop-blur-xl">
      <nav className={`${LANDING_CONTAINER} flex h-[72px] items-center justify-between px-5 sm:px-8`}>
        <Link href="/" className="font-landing-serif text-2xl font-semibold tracking-[-0.04em] text-[#282522]">
          Koraku
        </Link>

        <div className="flex items-center gap-2">
          <Link
            href="#models"
            className="hidden px-4 py-2 text-[13px] font-medium text-stone-800 transition hover:text-black sm:inline-flex"
          >
            Models
          </Link>
          <Link
            href="#integrations"
            className="hidden px-4 py-2 text-[13px] font-medium text-stone-800 transition hover:text-black sm:inline-flex"
          >
            Integrations
          </Link>
          <Link
            href="/sign-in"
            className="rounded-full border border-black/10 bg-white px-4 py-2 text-[13px] font-medium text-stone-800 shadow-sm transition hover:bg-stone-50"
          >
            Log in
          </Link>
          <Link
            href={APP_BASE}
            className="rounded-full bg-[#171717] px-4 py-2 text-[13px] font-medium text-white shadow-[0_8px_18px_rgba(0,0,0,0.2)] transition hover:-translate-y-0.5"
          >
            Open app
          </Link>
        </div>
      </nav>
    </header>
  );
}
