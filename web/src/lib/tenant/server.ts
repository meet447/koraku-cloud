import type { SupabaseClient } from "@supabase/supabase-js";
import { cookies } from "next/headers";
import { ORG_ID_COOKIE, ORG_ID_HEADER } from "@/lib/tenant/constants";
import { deleteCachedKeys, getCachedJson, setCachedJson } from "../koraku-redis";

export type OrgSummary = {
  id: string;
  name: string;
  kind: string;
  role: string;
  isDefault: boolean;
};

function orgIdCookieOptions() {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 365,
  };
}

/** Persist the active organization in the httpOnly tenant cookie. */
export async function persistOrgIdCookie(orgId: string): Promise<void> {
  const jar = await cookies();
  jar.set(ORG_ID_COOKIE, orgId, orgIdCookieOptions());
}

/** Ensure the signed-in user has a default personal organization (Supabase RPC). */
export async function ensureDefaultOrgId(
  supabase: SupabaseClient,
  userId: string,
): Promise<string | null> {
  const { data, error } = await supabase.rpc("koraku_ensure_personal_org", {
    p_user_id: userId,
  });
  if (error || data == null) {
    return null;
  }
  return String(data);
}

export async function listUserOrgs(
  supabase: SupabaseClient,
  userId: string,
): Promise<OrgSummary[]> {
  const { data: memberships, error } = await supabase
    .from("koraku_org_member")
    .select("org_id, role, is_default, koraku_organization(id, name, kind)")
    .eq("user_id", userId);
  if (error || !memberships?.length) {
    return [];
  }
  const out: OrgSummary[] = [];
  for (const row of memberships) {
    const org = row.koraku_organization as
      | { id: string; name: string; kind: string }
      | { id: string; name: string; kind: string }[]
      | null;
    const o = Array.isArray(org) ? org[0] : org;
    if (!o?.id) continue;
    out.push({
      id: String(o.id),
      name: String(o.name ?? "Workspace"),
      kind: String(o.kind ?? "personal"),
      role: String(row.role ?? "member"),
      isDefault: Boolean(row.is_default),
    });
  }
  return out.sort((a, b) => Number(b.isDefault) - Number(a.isDefault));
}

export async function resolveActiveOrgId(
  supabase: SupabaseClient,
  userId: string,
): Promise<string | null> {
  const jar = await cookies();
  const fromCookie = jar.get(ORG_ID_COOKIE)?.value?.trim();
  if (fromCookie) {
    const cacheKey = `org-verify:${userId}:${fromCookie}`;
    try {
      const cached = await getCachedJson<boolean>(cacheKey);
      if (cached) {
        return fromCookie;
      }
    } catch {
      /* ignore cache read errors */
    }

    const { data } = await supabase
      .from("koraku_org_member")
      .select("org_id")
      .eq("user_id", userId)
      .eq("org_id", fromCookie)
      .maybeSingle();
    if (data?.org_id) {
      try {
        // Cache organization verification for 5 minutes (300 seconds)
        await setCachedJson(cacheKey, true, 300);
      } catch {
        /* ignore cache write errors */
      }
      return String(data.org_id);
    }

    try {
      await deleteCachedKeys(cacheKey);
    } catch {
      /* ignore cache delete errors */
    }
  }

  const healed = await ensureDefaultOrgId(supabase, userId);
  if (healed && healed !== fromCookie) {
    await persistOrgIdCookie(healed);
  }
  return healed;
}

/** Forward validated tenant scope to the Python API (after Bearer auth is applied). */
export async function applyTenantHeadersFromCookies(
  headers: Headers,
  supabase: SupabaseClient,
  userId: string,
): Promise<void> {
  const orgId = await resolveActiveOrgId(supabase, userId);
  if (orgId) {
    headers.set(ORG_ID_HEADER, orgId);
  }
}
