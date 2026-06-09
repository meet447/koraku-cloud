import { korakuFetchJson, korakuFetchOk } from "@/lib/koraku-fetch";

export type AdminDashboardStats = {
  period_start?: string;
  org_count?: number;
  total_credits_used?: number;
  orgs_over_80_pct?: number;
  orgs_over_95_pct?: number;
  recent_adjustments?: Array<{
    org_id: string;
    credits: number;
    metadata?: Record<string, unknown>;
    created_at: string;
  }>;
};

export type AdminOrgSummary = {
  id: string;
  name: string;
  kind: string;
  created_at: string;
  matched_email?: string;
  matched_user_id?: string;
  member_role?: string;
};

export type AdminOrgDetail = {
  org: AdminOrgSummary;
  usage: {
    plan: string;
    credits_limit: number;
    credits_used: number;
    credits_remaining: number;
    percent_used: number;
    period_start: string;
    period_end: string;
    resets_in_days: number;
  };
  members: Array<{
    user_id: string;
    role: string;
    is_default: boolean;
    created_at: string;
  }>;
  admin_state: {
    org_id: string;
    suspended: boolean;
    suspend_reason: string;
    notes: string;
  };
  counts: Record<string, number>;
  activity: Array<{ credits: number; kind: string; created_at: string }>;
};

export type LedgerEntry = {
  id: string;
  credits: number;
  kind: string;
  metadata?: Record<string, unknown>;
  created_at: string;
  idempotency_key: string;
};

export async function fetchAdminMe(): Promise<{ admin: boolean; user_id?: string }> {
  return korakuFetchJson("/koraku-api/api/admin/me");
}

export async function fetchAdminDashboard(): Promise<{
  stats: AdminDashboardStats;
  audit: Array<Record<string, unknown>>;
}> {
  return korakuFetchJson("/koraku-api/api/admin/dashboard");
}

export async function searchAdminOrgs(query: string): Promise<AdminOrgSummary[]> {
  const params = new URLSearchParams({ q: query, limit: "25" });
  const data = await korakuFetchJson<{ items: AdminOrgSummary[] }>(
    `/koraku-api/api/admin/orgs/search?${params}`,
  );
  return data.items ?? [];
}

export async function fetchAdminOrg(orgId: string): Promise<AdminOrgDetail> {
  return korakuFetchJson(`/koraku-api/api/admin/orgs/${encodeURIComponent(orgId)}`);
}

export async function fetchAdminOrgLedger(orgId: string): Promise<LedgerEntry[]> {
  const data = await korakuFetchJson<{ items: LedgerEntry[] }>(
    `/koraku-api/api/admin/orgs/${encodeURIComponent(orgId)}/ledger?limit=100`,
  );
  return data.items ?? [];
}

export async function grantOrgCredits(
  orgId: string,
  payload: { grant_credits: number; reason: string },
): Promise<void> {
  await korakuFetchOk(`/koraku-api/api/admin/orgs/${encodeURIComponent(orgId)}/credits/grant`, {
    method: "POST",
    json: payload,
  });
}

export async function updateOrgPeriod(
  orgId: string,
  payload: { credits_limit?: number; plan?: string },
): Promise<void> {
  await korakuFetchOk(`/koraku-api/api/admin/orgs/${encodeURIComponent(orgId)}/credits/period`, {
    method: "PATCH",
    json: payload,
  });
}

export async function updateOrgAdminState(
  orgId: string,
  payload: { suspended?: boolean; suspend_reason?: string; notes?: string },
): Promise<void> {
  await korakuFetchOk(`/koraku-api/api/admin/orgs/${encodeURIComponent(orgId)}/state`, {
    method: "PATCH",
    json: payload,
  });
}
