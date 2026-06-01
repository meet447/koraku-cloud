"use client";

import { KorakuAppShell } from "@/components/KorakuAppShell";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return <KorakuAppShell>{children}</KorakuAppShell>;
}
