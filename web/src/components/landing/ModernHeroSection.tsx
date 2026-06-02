"use client";

import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { motion } from "motion/react";
import { APP_BASE } from "@/lib/app-path";
import { cn } from "@/lib/cn";

export const MODERN_HERO_VIDEO_SRC =
  "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260505_101331_74f9b798-3f00-4e86-8a01-377aa16ffeaa.mp4";

export function ModernHeroSection() {
  return (
    <section
      className={cn(
        "relative mx-auto flex h-[600px] w-full max-w-[1400px] flex-col overflow-hidden rounded-[48px]",
        "border border-slate-200/50 bg-white shadow-[0_40px_100px_-20px_rgba(0,0,0,0.03)]",
      )}
      aria-label="Koraku platform showcase"
    >
      <div className="pointer-events-none absolute inset-0 z-0 select-none overflow-hidden">
        <video
          autoPlay
          loop
          muted
          playsInline
          className="h-full w-full scale-105 object-cover transition-transform duration-1000"
          aria-hidden
        >
          <source src={MODERN_HERO_VIDEO_SRC} type="video/mp4" />
        </video>
      </div>

      <div className="relative z-20 flex flex-1 flex-col items-start px-8 pt-12 md:px-16 md:pt-16">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          className="max-w-xl text-left"
        >
          <h2 className="font-landing-display text-[42px] font-medium leading-[1.08] tracking-tight text-[#0a1b33] md:text-[56px]">
            Foundation of your
            <br />
            living memory
          </h2>
          <p className="mt-5 max-w-md font-landing-sans text-[14px] leading-relaxed text-[#64748b] md:text-[15px]">
            Koraku remembers how you work, connects your apps, and turns everyday
            conversations into durable memory, chat, and safe automations.
          </p>
          <motion.div className="mt-8" whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
            <Link
              href={APP_BASE}
              className="inline-flex items-center rounded-full bg-[#0a152d] px-7 py-3 font-landing-sans text-sm font-semibold text-white transition-colors hover:bg-[#0f1f3d]"
            >
              Open Koraku
            </Link>
          </motion.div>
        </motion.div>
      </div>

      <div className="absolute bottom-10 left-1/2 z-30 -translate-x-1/2">
        <motion.nav
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.25, ease: "easeOut" }}
          className="flex items-center rounded-full border border-slate-200/40 bg-white/90 px-1.5 py-1.5 shadow-[0_12px_40px_rgba(0,0,0,0.08)] backdrop-blur-2xl"
          aria-label="Quick links"
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-full border border-slate-100 bg-white text-sm text-[#0a1b33] shadow-sm">
            ✦
          </div>

          <Link
            href={`${APP_BASE}/memory`}
            className="px-4 py-2 text-[12px] font-semibold text-slate-500 transition-colors hover:text-[#0a1b33]"
          >
            Memory
          </Link>
          <Link
            href="https://github.com/meet447/koraku-cloud#readme"
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 text-[12px] font-semibold text-slate-500 transition-colors hover:text-[#0a1b33]"
          >
            Docs
          </Link>

          <Link
            href="/sign-up?next=/app/onboarding"
            className="ml-1 flex items-center gap-1 rounded-full border border-slate-200/60 bg-white px-5 py-2 text-[12px] font-semibold text-[#0a1b33] shadow-sm transition-all hover:border-slate-300"
          >
            Get started
            <ChevronRight className="h-3.5 w-3.5" aria-hidden />
          </Link>
        </motion.nav>
      </div>
    </section>
  );
}
