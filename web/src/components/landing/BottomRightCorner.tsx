"use client";

import Link from "next/link";
import { ArrowUpRight, ChevronRight } from "lucide-react";
import { motion } from "motion/react";
import { LANDING, landingText } from "@/lib/landing-theme";

export function BottomRightCorner() {
  return (
    <motion.div
      initial={{ y: 20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.8, delay: 0.4 }}
      className="absolute bottom-0 right-0 flex items-center gap-3 rounded-tl-[1.5rem] p-3 pl-8 pt-5 sm:gap-4 sm:rounded-tl-[2rem] sm:p-4 sm:pl-10 sm:pt-6 md:gap-6 md:rounded-tl-[3.5rem] md:p-6 md:pl-14 md:pt-8"
      style={{ backgroundColor: LANDING.bg }}
    >
      <div className="pointer-events-none absolute -top-[1.5rem] right-0 h-[1.5rem] w-[1.5rem] sm:-top-[2rem] sm:h-[2rem] sm:w-[2rem] md:-top-[3.5rem] md:h-[3.5rem] md:w-[3.5rem]">
        <svg width="100%" height="100%" viewBox="0 0 56 56" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M56 56V0C56 30.9279 30.9279 56 0 56H56Z" fill={LANDING.bg} />
        </svg>
      </div>
      <div className="pointer-events-none absolute -left-[1.5rem] bottom-0 h-[1.5rem] w-[1.5rem] sm:-left-[2rem] sm:h-[2rem] sm:w-[2rem] md:-left-[3.5rem] md:h-[3.5rem] md:w-[3.5rem]">
        <svg width="100%" height="100%" viewBox="0 0 56 56" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M56 56H0C30.9279 56 56 30.9279 56 0V56Z" fill={LANDING.bg} />
        </svg>
      </div>

      <div className="flex h-10 w-10 items-center justify-center rounded-full border border-orange-200/60 bg-orange-50/80 md:h-14 md:w-14">
        <ArrowUpRight className={`h-5 w-5 md:h-6 md:w-6 ${landingText.accent}`} aria-hidden />
      </div>

      <div className="flex flex-col">
        <span className={`text-[16px] font-normal md:text-[20px] ${landingText.headline}`}>
          Documentation
        </span>
        <Link
          href="https://github.com/meet447/koraku-cloud#readme"
          target="_blank"
          rel="noopener noreferrer"
          className={`flex cursor-pointer items-center gap-1 transition-colors hover:opacity-80 ${landingText.accent}`}
        >
          <span className="text-[12px] font-normal md:text-[15px]">Self-host guide</span>
          <ChevronRight className="h-4 w-4" aria-hidden />
        </Link>
      </div>
    </motion.div>
  );
}
