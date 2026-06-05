import { getCachedJson, setCachedJson } from "./koraku-redis";
import type { LocalContextPlace } from "./local-context";

type GeoCoords = { city: string; latitude: number; longitude: number };

function isPrivateOrLocalIp(ip: string): boolean {
  if (ip === "::1" || ip === "127.0.0.1" || ip.startsWith("127.")) return true;
  if (ip.startsWith("10.") || ip.startsWith("192.168.") || ip.startsWith("169.254.")) {
    return true;
  }
  if (/^172\.(1[6-9]|2\d|3[01])\./.test(ip)) return true;
  if (ip.startsWith("fc") || ip.startsWith("fd") || ip.startsWith("fe80:")) return true;
  return false;
}

export function clientIpFromRequest(request: Request): string | null {
  const forwarded = request.headers.get("x-forwarded-for");
  if (forwarded) {
    const first = forwarded.split(",")[0]?.trim();
    if (first && !isPrivateOrLocalIp(first)) return first;
  }
  const realIp = request.headers.get("x-real-ip")?.trim();
  if (realIp && !isPrivateOrLocalIp(realIp)) return realIp;
  const cfIp = request.headers.get("cf-connecting-ip")?.trim();
  if (cfIp && !isPrivateOrLocalIp(cfIp)) return cfIp;
  return null;
}

function parseGeoJsPayload(data: {
  city?: string;
  latitude?: string | number;
  longitude?: string | number;
}): GeoCoords | null {
  const city = data.city?.trim();
  const lat = Number(data.latitude);
  const lon = Number(data.longitude);
  if (city && Number.isFinite(lat) && Number.isFinite(lon)) {
    return { city, latitude: lat, longitude: lon };
  }
  return null;
}

async function fetchGeoCoords(clientIp: string | null): Promise<GeoCoords | null> {
  const geoJsUrl =
    clientIp && !isPrivateOrLocalIp(clientIp)
      ? `https://get.geojs.io/v1/ip/geo/${encodeURIComponent(clientIp)}.json`
      : "https://get.geojs.io/v1/ip/geo.json";

  try {
    const res = await fetch(geoJsUrl, {
      cache: "no-store",
      signal: AbortSignal.timeout(8_000),
    });
    if (res.ok) {
      const parsed = parseGeoJsPayload(
        (await res.json()) as {
          city?: string;
          latitude?: string | number;
          longitude?: string | number;
        },
      );
      if (parsed) return parsed;
    }
  } catch {
    /* try next provider */
  }

  try {
    const res = await fetch("https://ipinfo.io/json", {
      cache: "no-store",
      signal: AbortSignal.timeout(8_000),
    });
    if (res.ok) {
      const data = (await res.json()) as { city?: string; loc?: string };
      const city = data.city?.trim();
      const [latRaw, lonRaw] = (data.loc ?? "").split(",");
      const lat = Number(latRaw);
      const lon = Number(lonRaw);
      if (city && Number.isFinite(lat) && Number.isFinite(lon)) {
        return { city, latitude: lat, longitude: lon };
      }
    }
  } catch {
    /* try next provider */
  }

  try {
    const ipApiPath =
      clientIp && !isPrivateOrLocalIp(clientIp)
        ? `http://ip-api.com/json/${encodeURIComponent(clientIp)}?fields=status,city,lat,lon`
        : "http://ip-api.com/json/?fields=status,city,lat,lon";
    const res = await fetch(ipApiPath, {
      cache: "no-store",
      signal: AbortSignal.timeout(8_000),
    });
    if (res.ok) {
      const data = (await res.json()) as {
        status?: string;
        city?: string;
        lat?: number;
        lon?: number;
      };
      const city = data.city?.trim();
      if (
        data.status === "success" &&
        city &&
        typeof data.lat === "number" &&
        typeof data.lon === "number"
      ) {
        return { city, latitude: data.lat, longitude: data.lon };
      }
    }
  } catch {
    /* exhausted */
  }

  return null;
}

async function fetchWttrTemperatureC(city: string): Promise<number | null> {
  const res = await fetch(
    `https://wttr.in/${encodeURIComponent(city)}?format=j1`,
    {
      cache: "no-store",
      signal: AbortSignal.timeout(8_000),
      headers: { Accept: "application/json" },
    },
  );
  if (!res.ok) return null;
  const data = (await res.json()) as {
    current_condition?: Array<{ temp_C?: string }>;
  };
  const raw = data.current_condition?.[0]?.temp_C;
  if (raw == null) return null;
  const t = Number.parseInt(String(raw), 10);
  return Number.isFinite(t) ? t : null;
}

async function fetchTemperatureC(coords: GeoCoords): Promise<number | null> {
  try {
    const wttr = await fetchWttrTemperatureC(coords.city);
    if (wttr != null) return wttr;
  } catch {
    /* fall through */
  }

  try {
    const params = new URLSearchParams({
      latitude: String(coords.latitude),
      longitude: String(coords.longitude),
      current: "temperature_2m",
    });
    const res = await fetch(
      `https://api.open-meteo.com/v1/forecast?${params}`,
      { cache: "no-store", signal: AbortSignal.timeout(8_000) },
    );
    if (res.ok) {
      const weather = (await res.json()) as {
        current?: { temperature_2m?: number };
      };
      const t = weather.current?.temperature_2m;
      if (typeof t === "number" && Number.isFinite(t)) {
        return Math.round(t);
      }
    }
  } catch {
    /* optional */
  }

  return null;
}

/** Resolve city + temperature on the server (uses caller IP when provided). */
export async function resolveLocalContextPlace(
  clientIp: string | null,
): Promise<LocalContextPlace | null> {
  const ipKey = clientIp || "unknown-ip";
  const cacheKey = `local-context:${ipKey}`;
  try {
    const cached = await getCachedJson<LocalContextPlace>(cacheKey);
    if (cached) return cached;
  } catch {
    /* ignore cache read errors */
  }

  const coords = await fetchGeoCoords(clientIp);
  if (!coords) return null;

  const temperatureC = await fetchTemperatureC(coords);
  const place: LocalContextPlace = { city: coords.city, temperatureC };

  try {
    // Cache for 1 hour (3600 seconds)
    await setCachedJson(cacheKey, place, 3600);
  } catch {
    /* ignore cache write errors */
  }

  return place;
}
