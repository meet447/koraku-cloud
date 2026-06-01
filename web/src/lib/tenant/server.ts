import type { SupabaseClient } from "@supabase/supabase-js";
import { cookies } from "next/headers";
import { ORG_ID_COOKIE, ORG_ID_HEADER } from "@/lib/tenant/constants";

export type OrgSummary = {
  id: string;
  name: string;
  kind: string;
  role: string;
  isDefault: boolean;
};

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
    const { data } = await supabase
      .from("koraku_org_member")
      .select("org_id")
      .eq("user_id", userId)
      .eq("org_id", fromCookie)
      .maybeSingle();
    if (data?.org_id) {
      return String(data.org_id);
    }
  }
  return ensureDefaultOrgId(supabase, userId);
}

/** Forward tenant scope to the Python API (after Bearer auth is applied). */
export async function applyTenantHeadersFromCookies(headers: Headers): Promise<void> {
  const jar = await cookies();
  const orgId = jar.get(ORG_ID_COOKIE)?.value?.trim();
  if (orgId) {
    headers.set(ORG_ID_HEADER, orgId);
  }
}
