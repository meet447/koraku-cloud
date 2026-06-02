import type { User } from "@supabase/supabase-js";

export function getUserDisplayName(user: User): string {
  const fullName = (user.user_metadata?.full_name as string | undefined)?.trim();
  const name = (user.user_metadata?.name as string | undefined)?.trim();
  return fullName || name || user.email || "Account";
}

/** Google/GitHub OAuth avatars from Supabase `user_metadata`. */
export function getUserAvatarUrl(user: User): string | null {
  const meta = user.user_metadata ?? {};
  const candidates = [meta.avatar_url, meta.picture] as unknown[];
  for (const value of candidates) {
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return null;
}

export function getUserInitials(user: User): string {
  const label = getUserDisplayName(user);
  const parts = label.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0]![0] ?? ""}${parts[1]![0] ?? ""}`.toUpperCase();
  }
  return (label[0] ?? "?").toUpperCase();
}
