"use client";

import { Sparkles } from "lucide-react";
import { motion } from "motion/react";

export function HeroBadge() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className="mx-auto mb-4 flex w-fit items-center gap-2 rounded-full border border-orange-200 bg-landing-accentSoft px-4 py-1.5"
    >
      <Sparkles className="h-4 w-4 text-landing-accent" aria-hidden />
      <span className="text-[13px] font-medium text-landing-accentText">
        Your AI memory companion
      </span>
    </motion.div>
  );
}
