"use client";

import { Sparkles } from "lucide-react";
import { motion } from "motion/react";

export function HeroBadge() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className="mx-auto mb-3 flex w-fit items-center gap-2 rounded-full border border-orange-200/50 bg-white/65 px-4 py-2 backdrop-blur-md"
    >
      <Sparkles className="h-4 w-4 text-orange-700" aria-hidden />
      <span className="text-[14px] font-normal text-orange-800">Public beta</span>
    </motion.div>
  );
}
