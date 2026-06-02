import Link from "next/link";
import type { ReactNode } from "react";

export function KorakuAuthShell({
  title,
  description,
  children,
}: {
  title: string;
  description: ReactNode;
  children: ReactNode;
}) {
  return (
    <div>
      <p className="mb-4 inline-block rounded bg-white px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-stone-500 shadow-sm ring-1 ring-black/5">
        Account
      </p>
      <h1 className="landing-pixel-headline text-[2.8rem] font-semibold leading-[0.95] tracking-[-0.055em] text-[#282522] sm:text-[3.2rem]">
        {title}
      </h1>
      <p className="mt-4 text-base leading-7 text-stone-500">{description}</p>

      <div className="mt-8 rounded-lg border border-black/10 bg-white p-6 shadow-[10px_10px_0_rgba(0,0,0,0.04)] sm:p-8">
        {children}
      </div>

      <p className="mt-6 text-center text-sm text-stone-400 lg:hidden">
        <Link href="/" className="font-medium text-stone-600 transition hover:text-stone-900">
          ← Back to home
        </Link>
      </p>
    </div>
  );
}
