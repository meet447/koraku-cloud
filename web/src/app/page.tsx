import type { Metadata } from "next";
import { LandingPage } from "@/components/landing/LandingPage";

export const metadata: Metadata = {
  title: "Koraku — Fluid memory streams",
  description:
    "Your companion for memory, connected apps, and safe automations. Remember how you work and turn momentum into action.",
};

export default function Page() {
  return <LandingPage />;
}
