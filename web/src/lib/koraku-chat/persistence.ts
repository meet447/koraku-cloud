import {
  initialRunState,
  type RunState,
} from "@/lib/korakuReducer";
import {
  CLIENT_HISTORY_MAX_MESSAGES,
  CLIENT_HISTORY_MAX_TEXT_CHARS,
  type ChatMessage,
} from "@/lib/koraku-chat/types";
import { uid } from "@/lib/koraku-chat/session-utils";

function deserializeRunState(raw: unknown): RunState {
  const b = initialRunState();
  if (!raw || typeof raw !== "object") return b;
  const o = raw as Partial<RunState>;
  return {
    ...b,
    ...o,
    timeline: Array.isArray(o.timeline) ? o.timeline : b.timeline,
    pendingToolByUseId:
      o.pendingToolByUseId && typeof o.pendingToolByUseId === "object"
        ? o.pendingToolByUseId
        : b.pendingToolByUseId,
    blockKindByIndex:
      o.blockKindByIndex && typeof o.blockKindByIndex === "object"
        ? o.blockKindByIndex
        : b.blockKindByIndex,
    blockNameByIndex:
      o.blockNameByIndex && typeof o.blockNameByIndex === "object"
        ? o.blockNameByIndex
        : b.blockNameByIndex,
    partialJsonByIndex:
      o.partialJsonByIndex && typeof o.partialJsonByIndex === "object"
        ? o.partialJsonByIndex
        : b.partialJsonByIndex,
    sawToolUseThisTurn:
      typeof o.sawToolUseThisTurn === "boolean" ? o.sawToolUseThisTurn : b.sawToolUseThisTurn,
    assistantBubbleMode:
      o.assistantBubbleMode === "step" || o.assistantBubbleMode === "final"
        ? o.assistantBubbleMode
        : b.assistantBubbleMode,
    stepCaption: typeof o.stepCaption === "string" ? o.stepCaption : b.stepCaption,
    turnId: typeof o.turnId === "string" ? o.turnId : b.turnId,
    streamStatus:
      o.streamStatus === "streaming" ||
      o.streamStatus === "completed" ||
      o.streamStatus === "failed"
        ? o.streamStatus
        : b.streamStatus,
    sseAfter: typeof o.sseAfter === "number" ? o.sseAfter : b.sseAfter,
  };
}

export function apiRowToChatMessage(row: {
  id: string;
  role: string;
  contentJson: unknown;
}): ChatMessage | null {
  const c = row.contentJson;
  if (row.role === "user") {
    if (!c || typeof c !== "object") {
      return { id: row.id, role: "user", text: "" };
    }
    const o = c as Record<string, unknown>;
    const text = typeof o.text === "string" ? o.text : "";
    let images: { id: string; previewUrl: string }[] | undefined;
    if (Array.isArray(o.images)) {
      images = o.images
        .map((x) => {
          if (!x || typeof x !== "object") return null;
          const im = x as Record<string, unknown>;
          const id = typeof im.id === "string" ? im.id : uid();
          const previewUrl = typeof im.previewUrl === "string" ? im.previewUrl : "";
          return previewUrl ? { id, previewUrl } : null;
        })
        .filter((x): x is { id: string; previewUrl: string } => x != null);
    }
    return { id: row.id, role: "user", text, images: images?.length ? images : undefined };
  }
  if (row.role === "assistant") {
    const runRaw =
      c && typeof c === "object" && "run" in (c as object)
        ? (c as { run: unknown }).run
        : c;
    const run = deserializeRunState(runRaw);
    if (!run.turnId) {
      run.turnId = run.runId || row.id;
    }
    if (!run.runId && run.turnId) {
      run.runId = run.turnId;
    }
    return { id: row.id, role: "assistant", run };
  }
  return null;
}

export function messagesReadyToPersist(msgs: ChatMessage[]): ChatMessage[] {
  return msgs.filter((m) => {
    if (m.role !== "assistant") return true;
    if (m.run.streamStatus === "streaming") return true;
    return Boolean(m.run.assistantMarkdown.trim() || m.run.error?.trim());
  });
}

export function chatMessageToApiRow(m: ChatMessage): {
  id: string;
  role: string;
  contentJson: unknown;
} {
  if (m.role === "user") {
    const images = m.images?.map(({ id, previewUrl }) => ({
      id,
      previewUrl: previewUrl.length < 48_000 ? previewUrl : "",
    }));
    return {
      id: m.id,
      role: "user",
      contentJson: {
        text: m.text,
        ...(images?.some((i) => i.previewUrl) ? { images } : {}),
      },
    };
  }
  return { id: m.id, role: "assistant", contentJson: { run: m.run } };
}

export function chatMessagesToClientHistory(messages: ChatMessage[]): {
  role: "user" | "assistant";
  text: string;
}[] {
  return messages
    .slice(-CLIENT_HISTORY_MAX_MESSAGES)
    .map((m) => {
      const text = m.role === "user" ? m.text : m.run.assistantMarkdown;
      const clean = text.trim();
      if (!clean) return null;
      return {
        role: m.role,
        text:
          clean.length > CLIENT_HISTORY_MAX_TEXT_CHARS
            ? `${clean.slice(0, CLIENT_HISTORY_MAX_TEXT_CHARS - 1)}…`
            : clean,
      };
    })
    .filter((m): m is { role: "user" | "assistant"; text: string } => m != null);
}
