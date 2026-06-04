import { cookies } from "next/headers";
import { ORG_ID_COOKIE } from "@/lib/tenant/constants";
import {
  ensureDefaultOrgId,
  listUserOrgs,
} from "@/lib/tenant/server";
import { requireAuthedOrg } from "@/lib/supabase/route-auth";
import { requireSupabaseAuth } from "@/lib/supabase/server";

export const runtime = "nodejs";

export async function GET() {
  const authed = await requireAuthedOrg();
  if (!authed.ok) {
    return authed.response;
  }
  const { supabase, userId, orgId } = authed.ctx;

  const orgs = await listUserOrgs(supabase, userId);
  const active =
    orgs.find((o) => o.id === orgId) ??
    orgs[0] ??
    ({
      id: orgId,
      name: "Personal",
      kind: "personal",
      role: "owner",
      isDefault: true,
    } satisfies (typeof orgs)[0]);

  return Response.json({
    orgId,
    org: active,
    orgs,
  });
}

export async function POST(req: Request) {
  const auth = await requireSupabaseAuth();
  if (!auth.ok) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }
  const { supabase, userId } = auth;

  let body: { orgId?: string } = {};
  try {
    body = (await req.json()) as { orgId?: string };
  } catch {
    /* empty */
  }

  const requested = body.orgId?.trim();
  if (requested) {
    const { data } = await supabase
      .from("koraku_org_member")
      .select("org_id")
      .eq("user_id", userId)
      .eq("org_id", requested)
      .maybeSingle();
    if (!data?.org_id) {
      return Response.json({ error: "Forbidden" }, { status: 403 });
    }
    const jar = await cookies();
    jar.set(ORG_ID_COOKIE, requested, {
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      path: "/",
      maxAge: 60 * 60 * 24 * 365,
    });
    return Response.json({ orgId: requested });
  }

  const orgId = await ensureDefaultOrgId(supabase, userId);
  if (!orgId) {
    return Response.json({ error: "Could not create organization" }, { status: 503 });
  }
  const jar = await cookies();
  jar.set(ORG_ID_COOKIE, orgId, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 365,
  });
  return Response.json({ orgId });
}
