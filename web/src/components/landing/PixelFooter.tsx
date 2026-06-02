import Link from "next/link";
import { navItems } from "@/components/landing/landing-data";
import { LANDING_CONTAINER } from "@/components/landing/landing-layout";
import { APP_BASE } from "@/lib/app-path";

const footerColumns = [
  {
    title: "Product",
    links: navItems.map((item) => ({ label: item.label, href: item.href })),
  },
  {
    title: "Platform",
    links: [
      { label: "Open app", href: APP_BASE },
      { label: "Models", href: "#models" },
      { label: "Integrations", href: "#integrations" },
      { label: "Documentation", href: "https://github.com/meet447/koraku-cloud#readme", external: true },
    ],
  },
  {
    title: "Account",
    links: [
      { label: "Log in", href: "/sign-in" },
      { label: "Sign up", href: "/sign-up" },
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Privacy", href: "/privacy" },
      { label: "Terms", href: "/terms" },
    ],
  },
] as const;

export function PixelFooter() {
  return (
    <footer className="border-t border-black/10 bg-[#f5f4f1]">
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
            className="landing-pixel-headline pointer-events-none select-none font-landing-serif text-[clamp(5rem,18vw,12rem)] font-semibold leading-[0.82] tracking-[-0.07em] text-stone-900"
            aria-hidden
          >
            Koraku
          </p>
        </div>

        <div className="mt-6 flex flex-col gap-3 border-t border-black/10 pt-6 text-xs text-stone-400 sm:flex-row sm:items-center sm:justify-between">
          <p>Koraku © 2026</p>
          <div className="flex gap-5">
            <Link href="/privacy" className="transition hover:text-stone-600">
              Privacy
            </Link>
            <Link href="/terms" className="transition hover:text-stone-600">
              Terms
            </Link>
            <Link
              href="https://github.com/meet447/koraku-cloud"
              target="_blank"
              rel="noopener noreferrer"
              className="transition hover:text-stone-600"
            >
              GitHub
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
