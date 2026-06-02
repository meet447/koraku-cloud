import Link from "next/link";
import { PixelCloud, PixelEdge } from "@/components/landing/PixelArt";
import { APP_BASE } from "@/lib/app-path";

export function PixelFooter() {
  return (
    <footer className="relative overflow-hidden bg-[#f8f8f7] px-5 pb-20 pt-16 sm:px-8">
      <div className="mx-auto grid max-w-[980px] gap-10 md:grid-cols-[1fr_360px]">
        <div>
          <p className="landing-pixel-headline font-landing-serif text-4xl font-semibold leading-[0.95] tracking-[-0.06em] text-[#282522] sm:text-5xl">
            Run your day
            <br />
            <span className="text-stone-400">with AI agents</span>
          </p>
          <div className="mt-8 flex flex-wrap gap-x-8 gap-y-3 text-sm text-stone-600">
            {["Workspace", "Automations", "Models", "Integrations", "Safety"].map((item) => (
              <a key={item} href={`#${item.toLowerCase().replaceAll(" ", "-")}`} className="hover:text-stone-950">
                {item}
              </a>
            ))}
          </div>
          <p className="mt-12 text-xs text-stone-400">
            Copyright © 2026 Koraku. Built for agent desktops, model routing, integrations, and safer automation.
          </p>
        </div>

        <div className="rounded-lg border border-black/10 bg-white p-3 shadow-[10px_10px_0_rgba(0,0,0,0.05)]">
          <div className="relative min-h-[310px] overflow-hidden rounded-md bg-gradient-to-b from-[#4b4fd7] via-[#f08a5d] to-[#ffd08a] p-6 text-white">
            <PixelCloud className="right-6 top-10" />
            <div className="absolute bottom-0 left-0 right-0 h-24 bg-[#58b947]" />
            <div className="relative z-10 mt-28">
              <p className="text-2xl font-semibold leading-tight">
                Koraku gives every agent a desktop, apps, models, and memory.
              </p>
              <Link href={APP_BASE} className="mt-5 inline-flex rounded-lg bg-white px-4 py-2 text-sm font-bold text-slate-900">
                Open Koraku
              </Link>
            </div>
          </div>
        </div>
      </div>
      <PixelEdge />
    </footer>
  );
}
