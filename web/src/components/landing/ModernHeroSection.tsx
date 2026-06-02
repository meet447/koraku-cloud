"use client";

import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { motion } from "motion/react";
import { APP_BASE } from "@/lib/app-path";
import { MODERN_HERO_VIDEO } from "@/lib/landing-videos";
import { cn } from "@/lib/cn";

export function ModernHeroSection() {
  return (
    <section
      className={cn(
        "relative mx-auto flex h-[600px] w-full max-w-[1400px] flex-col overflow-hidden rounded-[48px]",
        "border border-slate-200/50 bg-white shadow-landing-hero",
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
          <source src={MODERN_HERO_VIDEO} type="video/mp4" />
        </video>
      </div>

      <div className="relative z-20 flex flex-1 flex-col items-start px-8 pt-12 md:px-16 md:pt-16">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          className="max-w-xl text-left"
        >
          <h2 className="font-landing-display text-[42px] font-medium leading-[1.08] tracking-tight text-landing-ink md:text-[56px]">
            Pick up right
            <br />
            where you left off
          </h2>
          <p className="mt-5 max-w-md text-sm leading-relaxed text-landing-muted md:text-[15px]">
            Chat with Koraku, hand off tasks, and let it keep your context, files, and
            connected apps in sync—every session builds on the last.
          </p>
          <motion.div className="mt-8" whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
            <Link
              href={APP_BASE}
              className="inline-flex items-center rounded-full bg-landing-ink px-7 py-3 text-sm font-semibold text-white transition-colors hover:bg-stone-800"
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
          className="flex items-center rounded-full border border-black/5 bg-white/90 px-1.5 py-1.5 shadow-landing-nav backdrop-blur-2xl"
          aria-label="Quick links"
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-full border border-orange-200 bg-landing-accentSoft text-sm text-landing-accent">
            ✦
          </div>

          <Link
            href="#features"
            className="px-4 py-2 text-xs font-semibold text-landing-soft transition-colors hover:text-landing-ink"
          >
            Features
          </Link>
          <Link
            href="/privacy"
            className="px-4 py-2 text-xs font-semibold text-landing-soft transition-colors hover:text-landing-ink"
          >
            Privacy
          </Link>

          <Link
            href="/sign-up?next=/app/onboarding"
            className="ml-1 flex items-center gap-1 rounded-full border border-black/5 bg-white px-5 py-2 text-xs font-semibold text-landing-ink shadow-sm transition-all hover:border-black/10"
          >
            Get started
            <ChevronRight className="h-3.5 w-3.5" aria-hidden />
          </Link>
        </motion.nav>
      </div>
    </section>
  );
}
