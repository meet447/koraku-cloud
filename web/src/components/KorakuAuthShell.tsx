import Link from "next/link";
import type { ReactNode } from "react";
import { BrandMark } from "@/components/BrandMark";

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
    <main className="flex min-h-dvh flex-col bg-koraku-panel text-koraku-ink">
      <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center px-6 py-16">
        <div className="mb-8 flex justify-center">
          <Link href="/" aria-label="Koraku home">
            <BrandMark size={56} />
          </Link>
        </div>
        <p className="text-xs font-bold uppercase tracking-[0.22em] text-orange-700">
          Account
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-koraku-ink">{title}</h1>
        <p className="mt-3 text-sm font-medium leading-relaxed text-koraku-muted">
          {description}
        </p>
        <div className="mt-8 rounded-[28px] bg-white p-6 shadow-sm ring-1 ring-neutral-200/80">
          {children}
        </div>
        <p className="mt-8 text-center text-sm font-medium text-koraku-muted">
          <Link href="/" className="font-semibold text-orange-700 underline-offset-2 hover:underline">
            ← Back to home
          </Link>
        </p>
      </div>
    </main>
  );
}
