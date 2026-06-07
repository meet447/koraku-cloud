"use client";

import { useEffect, type ReactNode } from "react";
import { KorakuChatProvider } from "@/context/KorakuChatContext";
import { useKorakuChat } from "@/hooks/useKorakuChat";
import { prefetchChatModelsCatalog } from "@/lib/chat-models-cache";

export function KorakuChatProviderWithState({ children }: { children: ReactNode }) {
  const chat = useKorakuChat();

  useEffect(() => {
    prefetchChatModelsCatalog();
  }, []);

  return (
    <KorakuChatProvider shell={chat.shell} thread={chat.thread}>
      {children}
    </KorakuChatProvider>
  );
}
