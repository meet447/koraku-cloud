"use client";

import { motion } from "motion/react";
import { BottomLeftCard } from "@/components/landing/BottomLeftCard";
import { BottomRightCorner } from "@/components/landing/BottomRightCorner";
import { HeroBadge } from "@/components/landing/HeroBadge";
import { Navbar } from "@/components/landing/Navbar";
import { LANDING_HERO_VIDEO } from "@/lib/landing-videos";

export function Hero() {
  return (
    <div className="flex h-screen w-full items-center justify-center bg-landing-stone p-3 md:p-5">
      <section className="group relative flex h-full w-full max-w-[1536px] flex-col items-center overflow-hidden rounded-[1.5rem] bg-white/10 shadow-none md:rounded-[3rem]">
        <video
          autoPlay
          muted
          loop
          playsInline
          className="absolute inset-0 z-0 h-full w-full object-cover object-[65%] lg:object-center"
          aria-hidden
        >
          <source src={LANDING_HERO_VIDEO} type="video/mp4" />
        </video>

        <div
          className="pointer-events-none absolute inset-0 z-[1] bg-landing-stone/45"
          aria-hidden
        />

        <div className="relative z-10 flex h-full w-full flex-col items-center">
          <Navbar />

          <div className="flex w-full max-w-4xl flex-col items-center px-6 pt-8 text-center">
            <HeroBadge />
            <motion.h1
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.8, delay: 0.2 }}
              className="mb-3 text-4xl font-normal leading-[1.05] tracking-tight text-landing-ink sm:text-5xl md:text-6xl lg:text-[78px]"
            >
              One companion for your
              <br />
              memory, work, and apps
            </motion.h1>
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.4 }}
              className="max-w-xl text-sm font-normal leading-relaxed text-landing-muted sm:text-base md:text-lg"
            >
              Koraku is a hosted AI companion that remembers how you work, organizes your
              second brain, connects your favorite apps, and runs safe automations—on the
              web or right from iMessage.
            </motion.p>
          </div>

          <BottomLeftCard />
          <BottomRightCorner />
        </div>
      </section>
    </div>
  );
}
