"use client";

import { motion } from "motion/react";
import { BottomLeftCard } from "@/components/landing/BottomLeftCard";
import { BottomRightCorner } from "@/components/landing/BottomRightCorner";
import { HeroBadge } from "@/components/landing/HeroBadge";
import { Navbar } from "@/components/landing/Navbar";
import { LANDING, LANDING_VIDEO_SRC, landingText } from "@/lib/landing-theme";

export function Hero() {
  return (
    <div
      className="flex h-screen w-full items-center justify-center p-3 md:p-5"
      style={{ backgroundColor: LANDING.bg }}
    >
      <section className="group relative flex h-full w-full max-w-[1536px] flex-col items-center overflow-hidden rounded-[1.5rem] bg-white/10 shadow-none md:rounded-[3rem]">
        <video
          autoPlay
          muted
          loop
          playsInline
          className="absolute inset-0 z-0 h-full w-full object-cover object-[65%] lg:object-center"
          aria-hidden
        >
          <source src={LANDING_VIDEO_SRC} type="video/mp4" />
        </video>

        {/* Warm wash so cool video footage matches Koraku stone/orange language */}
        <div
          className="pointer-events-none absolute inset-0 z-[1] bg-gradient-to-br from-amber-50/45 via-orange-50/20 to-[#f7f4ef]/55"
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
              className={`mb-2 text-4xl font-normal leading-[1.05] tracking-tight sm:text-5xl md:text-6xl lg:text-[80px] ${landingText.headline}`}
            >
              Fluid Memory Streams
            </motion.h1>
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.4 }}
              className={`max-w-xl text-sm font-normal leading-relaxed sm:text-base md:text-lg ${landingText.body}`}
            >
              Remember how you work, connect your apps, and turn everyday momentum into
              memory, chat, and safe automations—instantly.
            </motion.p>
          </div>

          <BottomLeftCard />
          <BottomRightCorner />
        </div>
      </section>
    </div>
  );
}
