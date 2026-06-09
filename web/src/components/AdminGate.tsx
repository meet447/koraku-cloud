"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { fetchAdminMe } from "@/lib/koraku-admin";
import { KorakuAppLoading } from "@/components/KorakuAppLoading";
import { KorakuAlert } from "@/components/KorakuAlert";

export function AdminGate({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<"loading" | "allowed" | "denied">("loading");

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const me = await fetchAdminMe();
        if (cancelled) return;
        if (me.admin) {
          setState("allowed");
          return;
        }
        setState("denied");
        router.replace("/app");
      } catch {
        if (!cancelled) {
          setState("denied");
          router.replace("/app");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  if (state === "loading") {
    return <KorakuAppLoading label="Checking admin access…" />;
  }

  if (state === "denied") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-white p-6">
        <KorakuAlert variant="error">
          Platform admin access required.{" "}
          <Link href="/app" className="underline">
            Back to app
          </Link>
        </KorakuAlert>
      </div>
    );
  }

  return <>{children}</>;
}
