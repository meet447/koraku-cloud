import type { ChatMessage, ChatSession, OutboundJob } from "@/lib/koraku-chat/types";

export function uid(): string {
  return crypto.randomUUID();
}

export function isDefaultChatTitle(title: string): boolean {
  const t = title.trim();
  return !t || t === "New chat";
}

export function isEmptyUnusedSession(
  sid: string,
  sessions: ChatSession[],
  messagesBySession: Record<string, ChatMessage[]>,
  streaming: ReadonlySet<string>,
): boolean {
  if (!sid || streaming.has(sid)) return false;
  if ((messagesBySession[sid] ?? []).length > 0) return false;
  const row = sessions.find((x) => x.id === sid);
  return isDefaultChatTitle(row?.title ?? "");
}

export function jobPreviewText(job: OutboundJob): string {
  const t = job.text.trim();
  if (t) {
    return t.length > 120 ? `${t.slice(0, 117)}…` : t;
  }
  if (job.images.length > 1) return `${job.images.length} images`;
  if (job.images.length === 1) return "Image";
  return "…";
}
