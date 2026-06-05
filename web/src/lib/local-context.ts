export type LocalContextPlace = {
  city: string;
  temperatureC: number | null;
};

const localTimeFormatter = new Intl.DateTimeFormat(undefined, {
  hour: "numeric",
  minute: "2-digit",
  hour12: true,
});

/** Compact clock label, e.g. `5:48PM`. */
export function formatLocalTime(date: Date, locale?: string): string {
  const formatter =
    locale != null
      ? new Intl.DateTimeFormat(locale, {
          hour: "numeric",
          minute: "2-digit",
          hour12: true,
        })
      : localTimeFormatter;
  return formatter.format(date).replace(/\s/g, "");
}

/** Browser: load place via same-origin API (avoids third-party blocks). */
export async function fetchLocalContextPlace(): Promise<LocalContextPlace | null> {
  try {
    const res = await fetch("/api/local-context", {
      cache: "no-store",
      signal: AbortSignal.timeout(12_000),
    });
    if (!res.ok) return null;
    const data = (await res.json()) as LocalContextPlace | { error?: string };
    if (typeof data === "object" && data && "city" in data && typeof data.city === "string") {
      return {
        city: data.city,
        temperatureC:
          typeof data.temperatureC === "number" ? data.temperatureC : null,
      };
    }
    return null;
  } catch {
    return null;
  }
}
