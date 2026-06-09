import type { ReactNode } from "react";
import Link from "next/link";
import { AdminGate } from "@/components/AdminGate";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <AdminGate>
      <div className="flex min-h-screen flex-col bg-neutral-50">
        <header className="border-b border-neutral-200/80 bg-white px-4 py-3 sm:px-6">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
            <div className="flex items-center gap-6">
              <Link href="/admin" className="text-sm font-bold text-koraku-ink">
                Koraku Admin
              </Link>
              <nav className="flex gap-4 text-sm font-semibold text-koraku-muted">
                <Link href="/admin" className="hover:text-koraku-ink">
                  Dashboard
                </Link>
                <Link href="/admin/orgs" className="hover:text-koraku-ink">
                  Organizations
                </Link>
              </nav>
            </div>
            <Link href="/app" className="text-xs font-semibold text-koraku-muted hover:text-koraku-ink">
              ← App
            </Link>
          </div>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6">{children}</main>
      </div>
    </AdminGate>
  );
}
