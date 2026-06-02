import Link from "next/link";
import { BrandMark } from "@/components/BrandMark";
import { navItems } from "@/components/landing/landing-data";

export function LeftRail() {
  return (
    <aside className="hidden h-screen overflow-hidden border-r border-black/10 bg-[#f8f8f7] px-6 py-8 lg:flex lg:flex-col">
      <Link href="/" className="inline-flex items-center gap-3">
        <BrandMark size={80} priority />
      </Link>

      <nav className="flex flex-1 flex-col justify-center">
        <div className="mb-4 inline-flex rounded bg-white px-2.5 py-1 text-sm font-semibold text-stone-900 shadow-sm">
          Koraku
        </div>
        <div className="grid gap-3">
          {navItems.map((item) => (
            <a
              key={item.label}
              href={item.href}
              className="text-base font-medium text-stone-400 transition hover:text-stone-900"
            >
              {item.label}
            </a>
          ))}
        </div>
      </nav>
    </aside>
  );
}
