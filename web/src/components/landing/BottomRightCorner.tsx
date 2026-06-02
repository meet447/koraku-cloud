"use client";

import Link from "next/link";
import { ArrowUpRight, ChevronRight } from "lucide-react";
import { motion } from "motion/react";

export function BottomRightCorner() {
  return (
    <motion.div
      initial={{ y: 20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.8, delay: 0.4 }}
      className="absolute bottom-0 right-0 flex items-center gap-3 rounded-tl-[1.5rem] bg-landing-stone p-3 pl-8 pt-5 sm:gap-4 sm:rounded-tl-[2rem] sm:p-4 sm:pl-10 sm:pt-6 md:gap-6 md:rounded-tl-[3.5rem] md:p-6 md:pl-14 md:pt-8"
    >
      <div className="pointer-events-none absolute -top-6 right-0 h-6 w-6 sm:-top-8 sm:h-8 sm:w-8 md:-top-14 md:h-14 md:w-14">
        <svg width="100%" height="100%" viewBox="0 0 56 56" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M56 56V0C56 30.9279 30.9279 56 0 56H56Z" className="fill-landing-stone" />
        </svg>
      </div>
      <div className="pointer-events-none absolute -left-6 bottom-0 h-6 w-6 sm:-left-8 sm:h-8 sm:w-8 md:-left-14 md:h-14 md:w-14">
        <svg width="100%" height="100%" viewBox="0 0 56 56" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M56 56H0C30.9279 56 56 30.9279 56 0V56Z" className="fill-landing-stone" />
        </svg>
      </div>

      <div className="flex h-10 w-10 items-center justify-center rounded-full border border-orange-200/60 bg-orange-50/80 md:h-14 md:w-14">
        <ArrowUpRight className="h-5 w-5 text-orange-700 md:h-6 md:w-6" aria-hidden />
      </div>

      <div className="flex flex-col">
        <span className="text-base font-normal text-landing-ink md:text-xl">Documentation</span>
        <Link
          href="https://github.com/meet447/koraku-cloud#readme"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-orange-700 transition-colors hover:opacity-80"
        >
          <span className="text-xs font-normal md:text-[15px]">Self-host guide</span>
          <ChevronRight className="h-4 w-4" aria-hidden />
        </Link>
      </div>
    </motion.div>
  );
}
