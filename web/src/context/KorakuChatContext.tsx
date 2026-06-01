"use client";

import { createContext, useContext, type ReactNode } from "react";
import type { KorakuChatShellApi, KorakuChatThreadApi } from "@/hooks/useKorakuChat";

const KorakuChatShellContext = createContext<KorakuChatShellApi | null>(null);
const KorakuChatThreadContext = createContext<KorakuChatThreadApi | null>(null);

export function KorakuChatProvider({
  shell,
  thread,
  children,
}: {
  shell: KorakuChatShellApi;
  thread: KorakuChatThreadApi;
  children: ReactNode;
}) {
  return (
    <KorakuChatShellContext.Provider value={shell}>
      <KorakuChatThreadContext.Provider value={thread}>{children}</KorakuChatThreadContext.Provider>
    </KorakuChatShellContext.Provider>
  );
}

export function useKorakuChatShell(): KorakuChatShellApi {
  const v = useContext(KorakuChatShellContext);
  if (!v) {
    throw new Error("useKorakuChatShell must be used under KorakuAppShell");
  }
  return v;
}

export function useKorakuChatThread(): KorakuChatThreadApi {
  const v = useContext(KorakuChatThreadContext);
  if (!v) {
    throw new Error("useKorakuChatThread must be used under KorakuAppShell");
  }
  return v;
}
