"use client";

import Image from "next/image";
import Link from "next/link";
import { motion } from "motion/react";
import { APP_BASE } from "@/lib/app-path";
import { LANDING_CONTAINER, LANDING_SECTION } from "@/components/landing/landing-layout";

export function HeroSection() {
  return (
    <section className={`border-b border-black/10 bg-[#f8f8f7] ${LANDING_SECTION}`}>
      <div className={LANDING_CONTAINER}>
        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          className="max-w-[820px] pt-2 sm:pt-4"
        >
          <h1 className="landing-pixel-headline font-landing-serif text-[4.5rem] font-semibold leading-[0.88] tracking-[-0.075em] text-[#24211f] sm:text-[6rem] lg:text-[6.8rem]">
            Automate your work with natural language
          </h1>
          <p className="mt-6 max-w-[620px] text-base font-medium leading-7 text-[#252525] sm:text-[17px]">
            Koraku plugs into your existing tools, gives agents their own desktop,
            routes tasks across models, and organizes workflows you already understand.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-5">
            <Link
              href={APP_BASE}
              className="inline-flex h-12 items-center justify-center rounded-md bg-[#171717] px-6 text-sm font-semibold text-white shadow-[0_8px_18px_rgba(0,0,0,0.2)] transition hover:-translate-y-0.5"
            >
              Open app
            </Link>
            <Link
              href="https://github.com/meet447/koraku-cloud#readme"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex h-12 items-center justify-center gap-2 text-sm font-semibold text-stone-700 transition hover:text-stone-950"
            >
              Watch launch video
              <span aria-hidden>›</span>
            </Link>
          </div>
        </motion.div>

        <div className="relative mt-12 overflow-hidden rounded-t-2xl border border-black/10 bg-[#d5d7d3] shadow-[0_24px_80px_-50px_rgba(0,0,0,0.35)] sm:mt-14">
          <Image
            src="/nectarahero.png"
            alt="Pixel-art sunset landscape with glowing butterflies and hills"
            width={1536}
            height={864}
            priority
            className="h-[380px] w-full object-cover sm:h-[500px] lg:h-[560px]"
          />
          <div className="absolute left-1/2 top-1/2 w-[min(520px,calc(100%-48px))] -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-white/40 bg-white/35 p-4 shadow-[0_16px_50px_rgba(0,0,0,0.18)] backdrop-blur-md">
            <p className="text-sm font-semibold leading-6 text-[#171717]">
              When an email is a bug report, create a Linear issue, summarize the thread,
              and ask before messaging the #bugs channel
            </p>
            <div className="mt-5 flex items-center justify-between">
              <span className="text-xl text-[#171717]">⌁</span>
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#171717] text-sm text-white">
                ↑
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
