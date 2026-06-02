"use client";

import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { motion } from "motion/react";

export function BottomLeftCard() {
  return (
    <motion.div
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.8, delay: 0.2 }}
      className="absolute bottom-28 left-auto right-4 flex w-fit min-w-[140px] flex-col gap-2 rounded-[1.2rem] border border-white/40 bg-white/45 p-3 backdrop-blur-xl md:bottom-6 md:left-6 md:right-auto md:min-w-[150px] md:gap-3 md:rounded-[1.5rem] md:p-4 lg:bottom-10 lg:left-10 lg:min-w-[180px] lg:gap-3 lg:rounded-[2.2rem] lg:p-5"
    >
      <div className="flex flex-col">
        <span className="text-2xl font-normal tracking-tight text-landing-ink md:text-3xl">
          3-in-1
        </span>
        <span className="text-[10px] font-normal uppercase tracking-wider text-landing-soft md:text-xs">
          Memory · Chat · Automations
        </span>
      </div>

      <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} className="self-start">
        <Link
          href="/sign-up?next=/app/onboarding"
          className="group flex items-center gap-2 rounded-full bg-white py-1.5 pl-1.5 pr-5 transition-colors hover:bg-orange-50/90"
        >
          <div className="flex items-center justify-center rounded-full bg-orange-100/80 p-1">
            <ArrowUpRight className="h-4 w-4 text-orange-800" aria-hidden />
          </div>
          <span className="text-[14px] font-normal text-landing-ink">Get started</span>
        </Link>
      </motion.div>
    </motion.div>
  );
}
