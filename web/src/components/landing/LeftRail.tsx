import Link from "next/link";
import { BrandMark } from "@/components/BrandMark";
import { navItems } from "@/components/landing/landing-data";

export function LeftRail() {
  return (
    <aside className="hidden h-screen overflow-hidden border-r border-black/10 bg-[#f8f8f7] px-7 py-8 lg:flex lg:flex-col">
      <Link href="/" className="inline-flex items-center">
        <BrandMark size={96} priority />
      </Link>

      <nav className="flex flex-1 flex-col justify-center">
        <div className="grid gap-5">
          {navItems.map((item) => (
            <a
              key={item.label}
              href={item.href}
              className="text-lg font-semibold tracking-[-0.02em] text-stone-400 transition hover:text-stone-900"
            >
              {item.label}
            </a>
          ))}
        </div>
      </nav>
    </aside>
  );
}
