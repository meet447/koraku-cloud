import type { ComposerAttachment, ComposerImage } from "@/components/Composer";
import type { RunState } from "@/lib/korakuReducer";

export type ChatMessage =
  | {
      id: string;
      role: "user";
      text: string;
      images?: { id: string; previewUrl: string }[];
      attachments?: { id: string; filename: string }[];
    }
  | { id: string; role: "assistant"; run: RunState };

export const MAX_CONCURRENT_CHAT_STREAMS = 3;

export const CLIENT_HISTORY_MAX_MESSAGES = 48;
export const CLIENT_HISTORY_MAX_TEXT_CHARS = 32_000;

export const EMPTY_THREAD_MESSAGES: ChatMessage[] = [];

export type ChatSession = {
  id: string;
  title: string;
  channel?: string;
  pinned?: boolean;
};

export type OutboundJob = {
  id: string;
  text: string;
  provider: string;
  model: string;
  dropdownModelLabel: string;
  images: ComposerImage[];
  attachments: ComposerAttachment[];
};

export type StreamingTurn = {
  threadId: string;
  assistantMsgId: string;
  turnId: string;
  startedAt: number;
};
