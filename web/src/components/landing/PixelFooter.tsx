import Link from "next/link";
import { navItems } from "@/components/landing/landing-data";
import { LANDING_CONTAINER, LANDING_FOOTER_BG } from "@/components/landing/landing-layout";
import { APP_BASE } from "@/lib/app-path";
import { legalPages } from "@/lib/legal-pages";
import { cn } from "@/lib/cn";

const footerColumns = [
  {
    title: "Product",
    links: navItems.map((item) => ({ label: item.label, href: item.href })),
  },
  {
    title: "Platform",
    links: [
      { label: "Open app", href: APP_BASE },
      { label: "How it works", href: "#how-it-works" },
      { label: "Models", href: "#models" },
      { label: "Integrations", href: "#integrations" },
    ],
  },
  {
    title: "Account",
    links: [
      { label: "Sign in", href: "/sign-in" },
      { label: "Contact", href: "/contact" },
    ],
  },
  {
    title: "Legal",
    links: legalPages.map((page) => ({ label: page.label, href: page.href })),
  },
] as const;

export function PixelFooter() {
  return (
    <footer className={cn("border-t border-black/10", LANDING_FOOTER_BG)}>
      <div className="h-1 bg-orange-600" aria-hidden />

      <div className={`${LANDING_CONTAINER} px-5 py-14 sm:px-8 lg:py-16`}>
        <div className="grid gap-10 border-b border-black/10 pb-12 sm:grid-cols-2 lg:grid-cols-4 lg:gap-8">
          {footerColumns.map((column) => (
            <div key={column.title}>
              <p className="mb-4 text-sm font-semibold text-stone-900">{column.title}</p>
              <ul className="space-y-3">
                {column.links.map((link) => (
                  <li key={link.label}>
                    {"external" in link && link.external ? (
                      <Link
                        href={link.href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-stone-500 transition hover:text-stone-900"
                      >
                        {link.label}
                      </Link>
                    ) : (
                      <Link href={link.href} className="text-sm text-stone-500 transition hover:text-stone-900">
                        {link.label}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="overflow-hidden pt-10 lg:pt-12">
          <p
            className="landing-pixel-headline pointer-events-none select-none text-[clamp(5rem,18vw,12rem)] font-semibold leading-[0.82] tracking-[-0.07em] text-stone-900"
            aria-hidden
          >
            Koraku
          </p>
        </div>

        <div className="mt-6 flex flex-col gap-3 border-t border-black/10 pt-6 text-xs text-stone-400 sm:flex-row sm:items-center sm:justify-between">
          <p>Koraku © 2026</p>
          <div className="flex flex-wrap gap-x-5 gap-y-2">
            {legalPages.map((page) => (
              <Link key={page.slug} href={page.href} className="transition hover:text-stone-600">
                {page.label}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}
