/** Sidebar chat row — matches ``useKorakuChat`` session shape. */
export type ChatSessionLike = {
  id: string;
  title: string;
  channel?: string;
  pinned?: boolean;
};

function isPinnedChatSession(session: ChatSessionLike): boolean {
  return session.channel === "imessage" || Boolean(session.pinned);
}

/** Keep iMessage / pinned threads first; preserve relative order within each group. */
export function sortChatSessions<T extends ChatSessionLike>(sessions: T[]): T[] {
  const pinned: T[] = [];
  const rest: T[] = [];
  for (const session of sessions) {
    if (isPinnedChatSession(session)) {
      pinned.push(session);
    } else {
      rest.push(session);
    }
  }
  return [...pinned, ...rest];
}
