import { createBrowserSupabaseClient } from "@/lib/supabase/browser";

/** Headers for same-origin fetch to Next or Koraku API routes that forward ``Authorization`` to Python. */
export async function supabaseAuthHeaders(): Promise<Record<string, string>> {
  const h: Record<string, string> = {};
  try {
    const supabase = createBrowserSupabaseClient();
    const { data } = await supabase.auth.getSession();
    if (data.session?.access_token) {
      h.Authorization = `Bearer ${data.session.access_token}`;
    }
  } catch {
    /* Supabase env missing */
  }
  return h;
}
