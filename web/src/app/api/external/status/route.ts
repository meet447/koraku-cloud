import { requireSupabaseAuth } from "@/lib/supabase/server";

export const runtime = "nodejs";

export async function GET() {
  const auth = await requireSupabaseAuth();
  if (!auth.ok) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }
  const { supabase, userId } = auth;

  let link: {
    phone_e164?: string;
    imessage_thread_id?: string;
    verified_at?: string;
  } | null = null;
  const linkRes = await supabase
    .from("koraku_phone_link")
    .select("phone_e164, imessage_thread_id, verified_at")
    .eq("user_id", userId)
    .maybeSingle();
  if (!linkRes.error) {
    link = linkRes.data;
  }

  const fromNumber =
    (process.env.SENDBLUE_FROM_NUMBER || process.env.NEXT_PUBLIC_SENDBLUE_FROM_NUMBER || "")
      .trim() || null;
  const configured = Boolean(
    process.env.SENDBLUE_API_KEY &&
      process.env.SENDBLUE_API_SECRET &&
      fromNumber,
  );

  return Response.json({
    configured,
    from_number: fromNumber,
    linked: Boolean(link?.phone_e164),
    phone_e164: link?.phone_e164 ?? null,
    imessage_thread_id: link?.imessage_thread_id ?? null,
    verified_at: link?.verified_at ?? null,
  });
}
