type SupabaseLikeError = {
  code?: unknown;
  message?: unknown;
  hint?: unknown;
  status?: unknown;
};

/**
 * Stable, narrow error shape suitable for production logs. The Supabase error
 * object can carry row data, parameter echoes, and internal hints — none of
 * that should land in shared log streams.
 */
export function safeError(label: string, err: unknown): void {
  if (err == null) {
    console.error(label, { code: "unknown" });
    return;
  }
  if (typeof err === "object") {
    const e = err as SupabaseLikeError;
    console.error(label, {
      code: typeof e.code === "string" ? e.code : "unknown",
      status: typeof e.status === "number" ? e.status : undefined,
    });
    return;
  }
  console.error(label, { code: "non_object" });
}
