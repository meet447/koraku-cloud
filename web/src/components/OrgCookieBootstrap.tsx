"use client";

import { useEffect, useRef } from "react";
import { bootstrapOrgCookie } from "@/lib/tenant/bootstrap-org";

/** Runs once per app mount; sets org cookie via Server Action when missing. */
export function OrgCookieBootstrap() {
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    void bootstrapOrgCookie();
  }, []);

  return null;
}
