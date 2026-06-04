"use client";

import { useEffect, useState } from "react";
import {
  fetchLocalContextPlace,
  formatLocalTime,
  type LocalContextPlace,
} from "@/lib/local-context";

export function useLocalContext() {
  const [time, setTime] = useState(() => formatLocalTime(new Date()));
  const [place, setPlace] = useState<LocalContextPlace | null>(null);

  useEffect(() => {
    const tick = () => setTime(formatLocalTime(new Date()));
    tick();
    const id = window.setInterval(tick, 30_000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    let cancelled = false;
    void fetchLocalContextPlace()
      .then((data) => {
        if (!cancelled) setPlace(data);
      })
      .catch(() => {
        if (!cancelled) setPlace(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return { time, place };
}
