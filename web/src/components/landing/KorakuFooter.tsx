"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef } from "react";
import { APP_BASE } from "@/lib/app-path";
import { FOOTER_VIDEO } from "@/lib/landing-videos";

function SocialIcon({
  href,
  label,
  children,
}: {
  href: string;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <a
      href={href}
      aria-label={label}
      target="_blank"
      rel="noopener noreferrer"
      className="flex h-9 w-9 items-center justify-center rounded-[9px] bg-[#0e1014] text-white shadow-landing-social transition-all hover:-translate-y-0.5 hover:bg-black hover:shadow-landing-social-hover [&_svg]:h-[15px] [&_svg]:w-[15px] [&_svg]:fill-current"
    >
      {children}
    </a>
  );
}

export function KorakuFooter() {
  const watermarkSvgRef = useRef<SVGSVGElement>(null);
  const watermarkTextRef = useRef<SVGTextElement>(null);

  const fitWatermark = useCallback(() => {
    const svg = watermarkSvgRef.current;
    const text = watermarkTextRef.current;
    if (!svg || !text) return;
    try {
      const bbox = text.getBBox();
      svg.setAttribute("viewBox", `${bbox.x} ${bbox.y} ${bbox.width} ${bbox.height}`);
    } catch {
      /* getBBox may fail before paint */
    }
  }, []);

  useEffect(() => {
    if (document.fonts?.ready) {
      void document.fonts.ready.then(fitWatermark);
    } else {
      window.addEventListener("load", fitWatermark);
      return () => window.removeEventListener("load", fitWatermark);
    }
  }, [fitWatermark]);

  useEffect(() => {
    window.addEventListener("resize", fitWatermark);
    return () => window.removeEventListener("resize", fitWatermark);
  }, [fitWatermark]);

  return (
    <section
      className="bg-white px-6 py-12 font-landing-body text-landing-body"
      aria-labelledby="koraku-footer-heading"
    >
      <h2 id="koraku-footer-heading" className="sr-only">
        Koraku footer
      </h2>

      <div className="mx-auto grid max-w-[1150px] grid-cols-1 items-stretch gap-4 min-[860px]:grid-cols-[350px_1fr]">
        <div className="relative flex min-h-[340px] flex-col justify-between overflow-hidden rounded-[28px] bg-landing-blue p-8 shadow-landing-footer-left min-[860px]:min-h-[340px] min-[860px]:gap-0 max-[859px]:min-h-0 max-[859px]:gap-10">
          <video
            className="pointer-events-none absolute inset-0 z-0 h-full w-full object-cover"
            autoPlay
            muted
            loop
            playsInline
            preload="auto"
            aria-hidden
          >
            <source src={FOOTER_VIDEO} type="video/mp4" />
          </video>

          <div className="relative z-[1] flex items-center gap-2.5">
            <div
              className="flex h-8 w-8 items-center justify-center rounded-lg border-[1.5px] border-white/85 bg-white/15 text-base font-bold tracking-tight text-white"
              aria-hidden
            >
              K
            </div>
            <span className="text-[22px] font-bold tracking-tight text-white">Koraku</span>
          </div>

          <div className="relative z-[1] mb-7 mt-auto">
            <p className="text-[19px] leading-[1.45] text-white">
              Smarter memory and automation,
              <br />
              <span className="text-white/65">powered by AI.</span>
            </p>
          </div>

          <div className="relative z-[1] flex items-center justify-between gap-3">
            <span className="font-landing-hand text-[17px] font-semibold tracking-wide text-white/90">
              Stay in touch!
            </span>
            <div className="flex gap-[7px]">
              <SocialIcon href="https://discord.com" label="Discord">
                <svg viewBox="0 0 24 24" aria-hidden>
                  <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z" />
                </svg>
              </SocialIcon>
              <SocialIcon href="https://x.com" label="X">
                <svg viewBox="0 0 24 24" aria-hidden>
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                </svg>
              </SocialIcon>
              <SocialIcon href="https://linkedin.com" label="LinkedIn">
                <svg viewBox="0 0 24 24" aria-hidden>
                  <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
                </svg>
              </SocialIcon>
              <SocialIcon href="https://github.com/meet447/koraku-cloud" label="GitHub">
                <svg viewBox="0 0 24 24" aria-hidden>
                  <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
                </svg>
              </SocialIcon>
            </div>
          </div>
        </div>

        <div className="relative flex flex-col justify-between overflow-visible rounded-[28px] bg-landing-footer p-10 shadow-landing-footer-right max-[560px]:p-6">
          <div
            className="absolute -top-9 right-10 z-10 flex flex-col items-start gap-1.5 max-[560px]:right-3 max-[560px]:-top-7"
            aria-hidden
          >
            <div className="flex h-24 w-24 -rotate-[10deg] items-center justify-center rounded-[22px] bg-landing-lucky-cube shadow-landing-lucky-cube max-[560px]:h-[72px] max-[560px]:w-[72px]">
              <span className="rotate-[10deg] text-[42px] font-bold leading-none tracking-tight text-white drop-shadow-[0_3px_6px_rgba(0,0,0,0.25)] max-[560px]:text-[32px]">
                K
              </span>
            </div>
            <div className="-rotate-[4deg] mt-1 flex items-center gap-1.5">
              <svg className="h-[22px] w-[22px] text-gray-400" viewBox="0 0 24 24">
                <path d="M3 20 C 6 14, 10 9, 18 5" stroke="currentColor" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M18 5 L 12 5" stroke="currentColor" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M18 5 L 18 11" stroke="currentColor" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span className="whitespace-nowrap font-landing-hand text-xl font-semibold text-gray-400">
                Feeling lucky?
              </span>
            </div>
          </div>

          <div className="pt-2">
            <div className="flex gap-[72px] max-[560px]:gap-10">
              <div>
                <p className="mb-[18px] font-landing-hand text-2xl font-semibold italic text-gray-400">
                  Navigation
                </p>
                <Link href={APP_BASE} className="mb-3.5 block text-sm font-semibold text-gray-900 transition-colors hover:text-[#1f65d6]">
                  How it works
                </Link>
                <Link href={`${APP_BASE}/memory`} className="mb-3.5 block text-sm font-semibold text-gray-900 transition-colors hover:text-[#1f65d6]">
                  Memory
                </Link>
                <Link href={`${APP_BASE}/connections`} className="mb-3.5 block text-sm font-semibold text-gray-900 transition-colors hover:text-[#1f65d6]">
                  Connections
                </Link>
                <Link href={`${APP_BASE}/automations`} className="mb-3.5 block text-sm font-semibold text-gray-900 transition-colors hover:text-[#1f65d6]">
                  Automations
                </Link>
                <Link href={`${APP_BASE}/settings`} className="mb-3.5 block text-sm font-semibold text-gray-900 transition-colors hover:text-[#1f65d6]">
                  Settings
                </Link>
              </div>
              <div>
                <p className="mb-[18px] font-landing-hand text-2xl font-semibold italic text-gray-400">
                  Company
                </p>
                <Link href="https://github.com/meet447/koraku-cloud#readme" target="_blank" rel="noopener noreferrer" className="mb-3.5 block text-sm font-semibold text-gray-900 transition-colors hover:text-[#1f65d6]">
                  Docs
                </Link>
                <Link href="/" className="mb-3.5 block text-sm font-semibold text-gray-900 transition-colors hover:text-[#1f65d6]">
                  About
                </Link>
                <Link href="/terms" className="mb-3.5 block text-sm font-semibold text-gray-900 transition-colors hover:text-[#1f65d6]">
                  Terms and Condition
                </Link>
                <Link href="/privacy" className="mb-3.5 block text-sm font-semibold text-gray-900 transition-colors hover:text-[#1f65d6]">
                  Privacy Policy
                </Link>
              </div>
            </div>
          </div>

          <div className="mt-12 flex items-end justify-between max-[560px]:mt-8 max-[560px]:flex-col max-[560px]:items-start max-[560px]:gap-6">
            <p className="text-[12.5px] font-medium text-gray-400">© 2025 Koraku. All rights reserved.</p>
            <div className="flex flex-col gap-3.5">
              <h4 className="text-[15px] font-normal leading-snug text-gray-500">
                AI moves fast.
                <br />
                <strong className="mt-0 block text-[19px] font-bold text-gray-900">
                  Stay ahead with Koraku.
                </strong>
              </h4>
              <form
                className="flex w-[310px] rounded-xl border border-gray-200 bg-white p-1.5 shadow-[0_2px_10px_rgba(0,0,0,0.04)] max-[560px]:w-full"
                onSubmit={(e) => e.preventDefault()}
              >
                <input
                  type="email"
                  name="email"
                  placeholder="Enter email address"
                  aria-label="Email address"
                  className="min-w-0 flex-1 bg-transparent px-3.5 py-[11px] text-[13.5px] text-gray-900 outline-none placeholder:text-gray-400"
                />
                <button
                  type="submit"
                  className="rounded-lg bg-[#111214] px-[22px] py-[11px] text-[13.5px] font-semibold text-white shadow-landing-subscribe transition-all hover:-translate-y-px hover:bg-black hover:shadow-landing-subscribe-hover"
                >
                  Subscribe
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>

      <div className="pointer-events-none relative z-0 mx-auto -mt-[60px] max-w-[1150px] select-none leading-none" aria-hidden>
        <svg
          ref={watermarkSvgRef}
          className="block h-auto w-full overflow-visible"
          viewBox="62 95 876 175"
          preserveAspectRatio="xMidYMid meet"
          xmlns="http://www.w3.org/2000/svg"
        >
          <text
            ref={watermarkTextRef}
            x="500"
            y="240"
            textAnchor="middle"
            fontSize="320"
            className="fill-black/[0.04] font-landing-body font-bold tracking-tight"
          >
            Koraku
          </text>
        </svg>
      </div>
    </section>
  );
}
