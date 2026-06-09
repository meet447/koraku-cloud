import { korakuFetchJson, korakuFetchOk } from "@/lib/koraku-fetch";
import { getClientCache, invalidateClientCache, setClientCache } from "@/lib/client-cache";

export type KorakuSkill = {
  slug: string;
  name: string;
  description: string;
  body: string;
  enabled: boolean;
};

export type SkillUpsertPayload = {
  name: string;
  description: string;
  body: string;
  enabled: boolean;
};

const CACHE_KEY = "koraku:skills";
const CACHE_TTL_MS = 30_000;

export function normalizeSkillSlug(raw: string): string {
  const slug = (raw || "").trim().toLowerCase();
  if (!slug || slug.length > 64) {
    throw new Error("Slug must be 1–64 characters.");
  }
  if (!/^[a-z0-9]/.test(slug)) {
    throw new Error("Slug must start with a letter or digit.");
  }
  if (!/^[a-z0-9-]+$/.test(slug)) {
    throw new Error("Slug may only contain lowercase letters, digits, and hyphens.");
  }
  return slug;
}

export async function loadSkills(options?: { force?: boolean }): Promise<KorakuSkill[]> {
  if (!options?.force) {
    const cached = getClientCache<KorakuSkill[]>(CACHE_KEY, CACHE_TTL_MS);
    if (cached) return cached;
  }
  const data = await korakuFetchJson<{ items: KorakuSkill[] }>("/koraku-api/api/skills");
  const items = (data.items ?? []).map((skill) => ({
    slug: skill.slug ?? "",
    name: skill.name ?? "",
    description: skill.description ?? "",
    body: skill.body ?? "",
    enabled: skill.enabled !== false,
  }));
  setClientCache(CACHE_KEY, items);
  return items;
}

export async function saveSkill(slug: string, payload: SkillUpsertPayload): Promise<void> {
  const normalized = normalizeSkillSlug(slug);
  await korakuFetchOk(`/koraku-api/api/skills/${encodeURIComponent(normalized)}`, {
    method: "PUT",
    json: payload,
  });
  invalidateClientCache(CACHE_KEY);
}

export async function deleteSkill(slug: string): Promise<void> {
  const normalized = normalizeSkillSlug(slug);
  await korakuFetchOk(`/koraku-api/api/skills/${encodeURIComponent(normalized)}`, {
    method: "DELETE",
  });
  invalidateClientCache(CACHE_KEY);
}

export function invalidateSkillsCache(): void {
  invalidateClientCache(CACHE_KEY);
}

export const SKILL_BODY_PLACEHOLDER = `---
name: my-skill
description: Use when the user asks about…
---

# My skill

Step-by-step instructions for the agent when this skill applies.
`;
