import {
  filePathFromToolInput,
  formatUrlForTimeline,
  humanizeToolErrorSnippet,
  humanizeToolExecution,
  pageToolLine,
} from "@/lib/toolEventLabels";
import { parseKorakuEventInner } from "@koraku/client";

export { parseKorakuEventInner } from "@koraku/client";

export type TimelineRow =
  | { id: string; kind: "thought"; seconds: number; body: string }
  | {
      id: string;
      kind: "tool";
      tool: string;
      label: string;
      detail?: string;
      ok?: boolean;
      /** Present while this row tracks an in-flight page fetch */
      callId?: string;
      /** Read / Write / Edit workspace-relative path (full, for downloads). */
      fileRelPath?: string;
      /** Completed tool stdout/stderr snippet (e.g. Bash); used for workspace file hints. */
      outputSummary?: string;
    }
  | {
      id: string;
      kind: "subagent";
      variant: "composio";
      toolkits: string[];
      /** Open until the server sends ``composio_end`` (``koraku.subagent``). */
      open: boolean;
      children: TimelineRow[];
    };

/** Composio integration worker stream (nested under a ``ComposioRun`` tool). */
export type ComposioSubagentMeta = { composio: true; toolkits: string[] };

export type RunState = {
  /** Client epoch ms when this assistant turn began (stable across sidebar remounts). */
  streamStartedAt: number | null;
  /** Per-turn server run id from ``koraku.started`` (optional; for logs / support). */
  runId: string;
  statusText: string;
  error: string | null;
  assistantMarkdown: string;
  /** Same text as the model dropdown option (not raw provider / API id). */
  dropdownModelLabel: string;
  metaModel: string;
  metaProvider: string;
  mode: string;
  maxSteps: number;
  toolsBadges: string[];
  timeline: TimelineRow[];
  activeThought: { started: number; text: string } | null;
  blockKindByIndex: Record<number, string>;
  blockNameByIndex: Record<number, string>;
  partialJsonByIndex: Record<number, string>;
  toolInvocations: number;
  /** Tool calls keyed by tool_use_id until a normalized completion event arrives. */
  pendingToolByUseId: Record<
    string,
    { tool: string; input: unknown; timelineRowId: string }
  >;
  /**
   * Latest ``subagent`` payload from ``stream_event`` (thinking/text). Used when finalizing
   * thoughts so rows nest under an open Composio worker group.
   */
  streamSubagentMeta: ComposioSubagentMeta | null;
  /** True after this turn emitted ``assistant_message`` with ``tool_use`` blocks. */
  sawToolUseThisTurn: boolean;
  /**
   * After tools: show a single live-updating line instead of the full streamed bubble until the
   * final text-only ``assistant_message`` arrives (avoids giant interim prose + tiny final).
   */
  assistantBubbleMode: "step" | "final";
  /** One-line preview for ``assistantBubbleMode === "step"`` (replaced each segment). */
  stepCaption: string | null;
};

function rid(): string {
  return `k-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

export function initialRunState(): RunState {
  return {
    streamStartedAt: null,
    runId: "",
    statusText: "",
    error: null,
    assistantMarkdown: "",
    dropdownModelLabel: "",
    metaModel: "",
    metaProvider: "",
    mode: "",
    maxSteps: 0,
    toolsBadges: [],
    timeline: [],
    activeThought: null,
    blockKindByIndex: {},
    blockNameByIndex: {},
    partialJsonByIndex: {},
    toolInvocations: 0,
    pendingToolByUseId: {},
    streamSubagentMeta: null,
    sawToolUseThisTurn: false,
    assistantBubbleMode: "final",
    stepCaption: null,
  };
}

function _metaFromSubagentPayload(sub: unknown): ComposioSubagentMeta | null {
  if (sub === true) {
    return { composio: true, toolkits: [] };
  }
  if (!sub || typeof sub !== "object") return null;
  const o = sub as Record<string, unknown>;
  if (!o.composio) return null;
  const tk = Array.isArray(o.toolkits)
    ? (o.toolkits as unknown[]).map((x) => String(x)).filter(Boolean)
    : [];
  return { composio: true, toolkits: tk };
}

function _hasOpenComposioNest(timeline: TimelineRow[]): boolean {
  for (let i = timeline.length - 1; i >= 0; i--) {
    const r = timeline[i];
    if (r?.kind === "subagent" && r.variant === "composio" && r.open) {
      return true;
    }
  }
  return false;
}

function _appendChildToOpenComposioNest(
  timeline: TimelineRow[],
  child: TimelineRow,
): TimelineRow[] {
  for (let i = timeline.length - 1; i >= 0; i--) {
    const r = timeline[i];
    if (r?.kind === "subagent" && r.variant === "composio" && r.open) {
      const next = [...timeline];
      const parent = r;
      next[i] = {
        ...parent,
        children: [...parent.children, child],
      };
      return next;
    }
  }
  return [...timeline, child];
}

function _appendTimelineRow(
  s: RunState,
  row: TimelineRow,
  meta: ComposioSubagentMeta | null,
): RunState {
  if (meta?.composio && _hasOpenComposioNest(s.timeline)) {
    return { ...s, timeline: _appendChildToOpenComposioNest(s.timeline, row) };
  }
  return { ...s, timeline: [...s.timeline, row] };
}

function _mapTimelineForToolRow(
  timeline: TimelineRow[],
  rowId: string,
  updater: (r: Extract<TimelineRow, { kind: "tool" }>) => TimelineRow,
): TimelineRow[] {
  return timeline.map((r) => {
    if (r.kind === "subagent") {
      return {
        ...r,
        children: _mapTimelineForToolRow(r.children, rowId, updater),
      };
    }
    if (r.kind === "tool" && r.id === rowId) {
      return updater(r);
    }
    return r;
  });
}

function _closeInnermostComposioNest(timeline: TimelineRow[]): TimelineRow[] {
  for (let i = timeline.length - 1; i >= 0; i--) {
    const r = timeline[i];
    if (r?.kind === "subagent" && r.variant === "composio" && r.open) {
      const next = [...timeline];
      next[i] = { ...r, open: false };
      return next;
    }
  }
  return timeline;
}

function finalizeThought(s: RunState): RunState {
  if (!s.activeThought) return s;
  const elapsed = Math.max(0, (Date.now() - s.activeThought.started) / 1000);
  const raw = s.activeThought.text.trim();
  const meta = s.streamSubagentMeta;
  if (!raw) {
    return { ...s, activeThought: null, streamSubagentMeta: null };
  }
  const body =
    raw.length > 14_000 ? `${raw.slice(0, 14_000)}…` : raw || "…";
  const row: TimelineRow = {
    id: rid(),
    kind: "thought",
    seconds: Math.round(elapsed * 10) / 10,
    body,
  };
  const cleared: RunState = {
    ...s,
    activeThought: null,
    streamSubagentMeta: null,
  };
  return _appendTimelineRow(cleared, row, meta);
}

/** Min matching suffix length before we treat streamed text as the same span as ``stepText``. */
const _RECLASSIFY_MIN_SUFFIX = 40;

function _longestCommonSuffixLength(a: string, b: string): number {
  let n = 0;
  const max = Math.min(a.length, b.length);
  while (n < max && a[a.length - 1 - n] === b[b.length - 1 - n]) {
    n += 1;
  }
  return n;
}

/**
 * When the model ends a step with ``tool_use``, the streamed ``text_delta`` body is planning,
 * not the user-facing final answer. Move it from the main bubble into a timeline thought.
 */
function _reclassifyStreamedTextToThought(
  prevMarkdown: string,
  stepText: string,
): { nextMarkdown: string; thoughtBody: string } | null {
  const t = stepText.trim();
  if (!t || !prevMarkdown) {
    return null;
  }
  if (prevMarkdown.endsWith(stepText)) {
    return {
      nextMarkdown: prevMarkdown.slice(0, -stepText.length),
      thoughtBody: stepText.length > 14_000 ? `${stepText.slice(0, 14_000)}…` : stepText,
    };
  }
  if (prevMarkdown.endsWith(t)) {
    return {
      nextMarkdown: prevMarkdown.slice(0, -t.length),
      thoughtBody: t.length > 14_000 ? `${t.slice(0, 14_000)}…` : t,
    };
  }
  const n = _longestCommonSuffixLength(prevMarkdown, stepText);
  if (n >= _RECLASSIFY_MIN_SUFFIX) {
    const suffix = prevMarkdown.slice(-n);
    return {
      nextMarkdown: prevMarkdown.slice(0, -n),
      thoughtBody: suffix.length > 14_000 ? `${suffix.slice(0, 14_000)}…` : suffix,
    };
  }
  return null;
}

/** Some models stream ``reasoning_content`` as thinking, then repeat the same opening in ``text``. */
const _MIN_THOUGHT_ECHO_STRIP = 24;

function _lastThoughtBodyFromTimeline(timeline: TimelineRow[]): string {
  function walk(rows: TimelineRow[]): string {
    for (let i = rows.length - 1; i >= 0; i--) {
      const r = rows[i];
      if (!r) continue;
      if (r.kind === "thought") {
        return String(r.body || "");
      }
      if (r.kind === "subagent") {
        const inner = walk(r.children);
        if (inner) return inner;
      }
    }
    return "";
  }
  return walk(timeline);
}

function _stripThoughtEchoPrefix(answer: string, thoughtBody: string): string {
  const tp = thoughtBody.trim();
  if (tp.length < _MIN_THOUGHT_ECHO_STRIP) {
    return answer;
  }
  const trimmed = answer.trimStart();
  if (!trimmed.startsWith(tp)) {
    return answer;
  }
  return trimmed.slice(tp.length).trimStart();
}

/** Single-line status derived from streamed step prose (not shown as a full bubble in ``step`` mode). */
function oneLineStepCaption(markdown: string): string {
  const t = markdown.replace(/\s+/g, " ").trim();
  if (!t) return "";
  const firstPara = t.split(/\n\n+/)[0] ?? t;
  const firstLine = firstPara.split("\n")[0]?.trim() ?? firstPara;
  return firstLine.length > 200 ? `${firstLine.slice(0, 197)}…` : firstLine;
}

function firstUrlInString(s: string): string | undefined {
  const m = s.match(/https?:\/\/[^\s)\]'">]+/);
  return m?.[0];
}

function urlFromToolInput(input: unknown): string | undefined {
  if (!input || typeof input !== "object") return undefined;
  const o = input as Record<string, unknown>;
  const u = o.url;
  return typeof u === "string" ? u.trim() : undefined;
}

function isPageTool(tool: string): boolean {
  return (
    tool === "WebPage" ||
    tool === "WebFetch" ||
    tool === "Firecrawl" ||
    tool === "FirecrawlMap"
  );
}

function toolResultText(block: Record<string, unknown>): string {
  const c = block.content;
  if (typeof c === "string") return c;
  if (Array.isArray(c)) {
    return c
      .map((part) => {
        if (typeof part === "string") return part;
        if (
          part &&
          typeof part === "object" &&
          (part as { type?: string }).type === "text" &&
          typeof (part as { text?: string }).text === "string"
        ) {
          return (part as { text: string }).text;
        }
        return "";
      })
      .join("");
  }
  return String(c ?? "");
}

function handleUserMessage(s: RunState, message: Record<string, unknown>): RunState {
  const content = message.content;
  const blocks = Array.isArray(content)
    ? (content as Record<string, unknown>[])
    : content && typeof content === "object"
      ? [content as Record<string, unknown>]
      : [];
  let next = { ...s };
  for (const block of blocks) {
    if (String(block.type || "") !== "tool_result") continue;
    const id = String(block.tool_use_id || "");
    const pending = id ? next.pendingToolByUseId[id] : undefined;
    const isErr = Boolean(block.is_error);
    const text = toolResultText(block);
    const tool = pending?.tool ?? "tool";
    const input = pending?.input;
    const urlHint = urlFromToolInput(input) ?? firstUrlInString(text);

    if (isPageTool(tool) && pending) {
      const { [id]: _drop, ...restPending } = next.pendingToolByUseId;
      next = { ...next, pendingToolByUseId: restPending };
      const rowId = pending.timelineRowId;
      const line = pageToolLine(
        tool,
        pending.input,
        isErr ? "error" : "done",
      );
      const detail =
        line.detail ?? (urlHint ? formatUrlForTimeline(urlHint) : undefined);
      const timeline = _mapTimelineForToolRow(next.timeline, rowId, (r) => ({
        ...r,
        label: line.label,
        detail: detail ?? r.detail,
        ok: !isErr,
        callId: undefined,
      }));
      next = { ...next, timeline };
      continue;
    }

    if (isPageTool(tool) && !pending && id) {
      const line = pageToolLine(tool, { url: urlHint } as Record<string, unknown>, isErr ? "error" : "done");
      const row: TimelineRow = {
        id: rid(),
        kind: "tool",
        tool,
        label: line.label,
        detail: line.detail ?? (urlHint ? formatUrlForTimeline(urlHint) : undefined),
        ok: !isErr,
      };
      next = _appendTimelineRow(next, row, null);
      continue;
    }

    if (isErr) {
      const row: TimelineRow = {
        id: rid(),
        kind: "tool",
        tool,
        label: `Failed: ${tool}`,
        detail: humanizeToolErrorSnippet(text) || urlHint,
        ok: false,
      };
      next = _appendTimelineRow(next, row, null);
    }
  }
  return next;
}

function handleToolEvent(s: RunState, event: Record<string, unknown>): RunState {
  const phase = String(event.phase || "");
  const id = String(event.tool_use_id || "");
  const tool = String(event.tool_name || "tool");
  const input = event.tool_input;
  const isErr = Boolean(event.is_error || phase === "failed");
  const outputSummary = typeof event.output_summary === "string" ? event.output_summary : "";
  const meta = _metaFromSubagentPayload(event.subagent);

  if (phase === "started") {
    const rowId = rid();
    const line = isPageTool(tool)
      ? pageToolLine(tool, input, "pending")
      : humanizeToolExecution(tool, input);
    const fileRelPath = filePathFromToolInput(tool, input);
    const row: TimelineRow = {
      id: rowId,
      kind: "tool",
      tool,
      label: line.label,
      detail: line.detail,
      ok: true,
      callId: id || undefined,
      ...(fileRelPath ? { fileRelPath } : {}),
    };
    const withRow = _appendTimelineRow(s, row, meta);
    return {
      ...withRow,
      pendingToolByUseId: id
        ? {
            ...withRow.pendingToolByUseId,
            [id]: { tool, input, timelineRowId: rowId },
          }
        : withRow.pendingToolByUseId,
      toolInvocations: withRow.toolInvocations + 1,
      statusText: `${line.label}…`,
    };
  }

  if (phase !== "completed" && phase !== "failed") {
    return s;
  }

  const pending = id ? s.pendingToolByUseId[id] : undefined;
  const eventTool = pending?.tool ?? tool;
  const eventInput = pending?.input ?? input;
  const { [id]: _drop, ...restPending } = s.pendingToolByUseId;
  const urlHint = urlFromToolInput(eventInput) ?? firstUrlInString(outputSummary);
  const page = isPageTool(eventTool);
  const line = page
    ? pageToolLine(eventTool, eventInput, isErr ? "error" : "done")
    : humanizeToolExecution(eventTool, eventInput);
  const label = isErr
    ? `Failed: ${eventTool}`
    : page
      ? line.label
      : line.label;
  const detail =
    (isErr ? humanizeToolErrorSnippet(outputSummary) : undefined) ||
    line.detail ||
    (urlHint ? formatUrlForTimeline(urlHint) : undefined);
  const fileRelPath =
    !isErr && (eventTool === "Read" || eventTool === "Write" || eventTool === "Edit")
      ? filePathFromToolInput(eventTool, eventInput)
      : undefined;

  const cappedOut =
    !isErr && outputSummary ? outputSummary.slice(0, 4000) : undefined;

  if (pending) {
    return {
      ...s,
      pendingToolByUseId: restPending,
      timeline: _mapTimelineForToolRow(s.timeline, pending.timelineRowId, (r) => ({
        ...r,
        label,
        detail: detail ?? r.detail,
        ok: !isErr,
        callId: undefined,
        ...(fileRelPath || r.fileRelPath
          ? { fileRelPath: fileRelPath ?? r.fileRelPath }
          : {}),
        ...(cappedOut ? { outputSummary: cappedOut } : {}),
      })),
      statusText: isErr ? `Failed: ${eventTool}` : `${line.label}`,
    };
  }

  const row: TimelineRow = {
    id: rid(),
    kind: "tool",
    tool: eventTool,
    label,
    detail,
    ok: !isErr,
    ...(fileRelPath ? { fileRelPath } : {}),
    ...(cappedOut ? { outputSummary: cappedOut } : {}),
  };
  return {
    ..._appendTimelineRow(s, row, meta),
    pendingToolByUseId: restPending,
    statusText: isErr ? `Failed: ${eventTool}` : `${line.label}`,
  };
}

function handleStreamEvent(s: RunState, ev: Record<string, unknown>): RunState {
  const t = ev.type as string | undefined;
  if (!t) return s;

  // Each agent react step is a new provider stream (new HTTP call). Without this, ``text_delta``
  // from step 2 appends to step 1's bubble text, so users see contradictions (e.g. "no results"
  // then a full summary) and duplicate closings.
  if (t === "message_start") {
    const stepMeta = _metaFromSubagentPayload(ev.subagent);
    let next = finalizeThought(s);
    const md = next.assistantMarkdown.trim();
    // Always clear the bubble for this new provider message so interim status lines replace each
    // other instead of stacking (previously we only cleared when ``sawToolUseThisTurn`` was true).
    const carryCaption = next.sawToolUseThisTurn && md.length > 0;
    const modePatch: Partial<RunState> = carryCaption
      ? {
          stepCaption: oneLineStepCaption(md),
          assistantBubbleMode: "step",
        }
      : next.sawToolUseThisTurn
        ? { stepCaption: null, assistantBubbleMode: "step" }
        : { stepCaption: null };

    return {
      ...next,
      assistantMarkdown: "",
      ...modePatch,
      streamSubagentMeta: stepMeta ?? null,
      blockKindByIndex: {},
      blockNameByIndex: {},
      partialJsonByIndex: {},
    };
  }

  if (t === "content_block_start") {
    const block = ev.content_block as Record<string, unknown> | undefined;
    const idx = ev.index as number;
    if (!block || typeof idx !== "number") return s;
    const bType = String(block.type || "");
    let next = { ...s, blockKindByIndex: { ...s.blockKindByIndex, [idx]: bType } };
    if (bType === "thinking") {
      next = finalizeThought(next);
      next = {
        ...next,
        activeThought: { started: Date.now(), text: "" },
      };
    }
    return next;
  }

  if (t === "content_block_delta") {
    const delta = ev.delta as Record<string, unknown> | undefined;
    const idx = ev.index as number;
    if (!delta || typeof idx !== "number") return s;
    const dt = String(delta.type || "");
    if (dt === "thinking_delta" && typeof delta.thinking === "string") {
      const sm = _metaFromSubagentPayload(ev.subagent) ?? s.streamSubagentMeta;
      if (!s.activeThought) {
        return {
          ...s,
          streamSubagentMeta: sm,
          activeThought: { started: Date.now(), text: delta.thinking },
        };
      }
      return {
        ...s,
        streamSubagentMeta: sm,
        activeThought: {
          ...s.activeThought,
          text: s.activeThought.text + delta.thinking,
        },
      };
    }
    if (dt === "text_delta" && typeof delta.text === "string") {
      const sm = _metaFromSubagentPayload(ev.subagent);
      const next = finalizeThought(
        sm ? { ...s, streamSubagentMeta: sm } : s,
      );
      const merged = next.assistantMarkdown + delta.text;
      const tb = _lastThoughtBodyFromTimeline(next.timeline);
      let out: RunState = {
        ...next,
        streamSubagentMeta: sm ?? next.streamSubagentMeta,
        assistantMarkdown: _stripThoughtEchoPrefix(merged, tb),
      };
      if (out.assistantBubbleMode === "step") {
        const line = oneLineStepCaption(out.assistantMarkdown);
        out = { ...out, stepCaption: line || out.stepCaption };
      }
      return out;
    }
    return s;
  }

  if (t === "content_block_stop") {
    const idx = ev.index as number;
    if (typeof idx !== "number") return s;
    const kind = s.blockKindByIndex[idx];
    let next = { ...s };
    if (kind === "thinking") {
      next = finalizeThought(next);
    }
    const { [idx]: _i, ...restPart } = next.partialJsonByIndex;
    const { [idx]: _k, ...restKind } = next.blockKindByIndex;
    const { [idx]: _n, ...restName } = next.blockNameByIndex;
    next = {
      ...next,
      partialJsonByIndex: restPart,
      blockKindByIndex: restKind,
      blockNameByIndex: restName,
    };
    return next;
  }

  if (t === "assistant_message") {
    const message = ev.message as Record<string, unknown> | undefined;
    if (!message) return s;
    const content = message.content;
    const blocks = Array.isArray(content)
      ? (content as Record<string, unknown>[])
      : [];
    let text = "";
    let hasToolUse = false;
    for (const b of blocks) {
      if (!b || typeof b !== "object") continue;
      const bt = String((b as { type?: string }).type || "");
      if (bt === "tool_use") {
        hasToolUse = true;
      }
      if (bt === "text" && typeof (b as { text?: string }).text === "string") {
        text += (b as { text: string }).text;
      }
    }
    const next = finalizeThought(s);
    const prev = next.assistantMarkdown;

    if (!text && !hasToolUse) {
      return s;
    }
    if (hasToolUse && !text.trim()) {
      return { ...next, sawToolUseThisTurn: true };
    }

    // Intermediate react step: prose before ``tool_use`` is step status — one line, not a
    // timeline ``thought`` blob (those were hiding the real final answer in the main bubble).
    if (hasToolUse && text.trim()) {
      const moved = _reclassifyStreamedTextToThought(prev, text);
      const withSaw: RunState = { ...next, sawToolUseThisTurn: true };
      if (moved) {
        const body = moved.thoughtBody.trim();
        if (body) {
          return {
            ...withSaw,
            assistantMarkdown: moved.nextMarkdown,
            streamSubagentMeta: null,
            assistantBubbleMode: "step",
            stepCaption: oneLineStepCaption(body) || withSaw.stepCaption,
          };
        }
        return {
          ...withSaw,
          assistantMarkdown: moved.nextMarkdown,
          streamSubagentMeta: null,
        };
      }
      return withSaw;
    }

    const thoughtEcho = _lastThoughtBodyFromTimeline(next.timeline);
    const textDed = _stripThoughtEchoPrefix(text, thoughtEcho);
    const prevDed = _stripThoughtEchoPrefix(prev, thoughtEcho);

    // After tool rounds we stream step narration into the bubble while ``assistantBubbleMode`` is
    // ``step``; the final ``assistant_message`` text is the user-facing answer and must replace
    // that buffer (otherwise every step stays concatenated with broken markdown).
    if (next.assistantBubbleMode === "step") {
      return {
        ...next,
        assistantMarkdown: textDed,
        assistantBubbleMode: "final",
        stepCaption: null,
      };
    }

    // ``text_delta`` appends here; some providers then emit ``assistant_message`` with only a
    // fragment of the same turn. Replacing always would flash full text → shorter text → user
    // sees the answer disappear. Prefer the longer body when the snapshot regresses.
    const md =
      prevDed.length > 0 && textDed.length < prevDed.length ? prevDed : textDed;
    return {
      ...next,
      assistantMarkdown: md,
      assistantBubbleMode: "final",
      stepCaption: null,
    };
  }

  return s;
}

export function applyKorakuSseEvent(
  s: RunState,
  outer: Record<string, unknown>,
): RunState {
  const typ = String(outer.type || "");
  let next = { ...s };

  if (typ === "koraku.started") {
    const d = outer.data as Record<string, unknown> | undefined;
    const rid = d?.runId != null ? String(d.runId) : "";
    next = {
      ...next,
      sawToolUseThisTurn: false,
      assistantBubbleMode: "final",
      stepCaption: null,
      ...(rid ? { runId: rid } : {}),
      ...(d && typeof d.model === "string"
        ? { metaModel: d.model, statusText: "Connecting…" }
        : {}),
    };
    return next;
  }

  if (typ === "koraku.route_decision") {
    const d = outer.data as Record<string, unknown> | undefined;
    if (d?.model) next = { ...next, metaModel: String(d.model) };
    const meta = d?.meta as Record<string, unknown> | undefined;
    if (meta?.provider) next = { ...next, metaProvider: String(meta.provider) };
    return next;
  }

  if (typ === "koraku.completed") {
    const d = outer.data as Record<string, unknown> | undefined;
    const failed = Boolean(d?.failed);
    const cancelled = Boolean(d?.cancelled);
    const err = d?.error != null ? String(d.error) : "";
    if (failed) {
      next = {
        ...next,
        error: err || "Run failed",
        statusText: "Failed",
      };
    } else if (cancelled) {
      next = { ...next, statusText: "Stopped", error: null };
    } else {
      next = { ...next, statusText: "Done", error: null };
    }
    next = finalizeThought(next);
    return {
      ...next,
      streamSubagentMeta: null,
      assistantBubbleMode: "final",
      stepCaption: null,
    };
  }

  if (typ === "koraku.turn_usage") {
    const d = outer.data as Record<string, unknown> | undefined;
    const inTok = typeof d?.input_tokens === "number" ? d.input_tokens : 0;
    const outTok = typeof d?.output_tokens === "number" ? d.output_tokens : 0;
    if (inTok + outTok > 0) {
      next = {
        ...next,
        statusText: `Thinking… · ${inTok + outTok} tok`,
      };
    }
    return next;
  }

  if (typ === "koraku.subagent") {
    const d = outer.data as Record<string, unknown> | undefined;
    if (!d) return next;
    const phase = String(d.phase || "");
    const tk = Array.isArray(d.toolkits)
      ? (d.toolkits as unknown[]).map((x) => String(x)).filter(Boolean)
      : [];
    if (phase === "composio_start") {
      let tl = next.timeline;
      if (_hasOpenComposioNest(tl)) {
        tl = _closeInnermostComposioNest(tl);
      }
      const group: TimelineRow = {
        id: rid(),
        kind: "subagent",
        variant: "composio",
        toolkits: tk,
        open: true,
        children: [],
      };
      return { ...next, timeline: [...tl, group] };
    }
    if (phase === "composio_end") {
      return {
        ...next,
        timeline: _closeInnermostComposioNest(next.timeline),
        streamSubagentMeta: null,
      };
    }
    return next;
  }

  if (typ === "koraku.event") {
    const inner = parseKorakuEventInner(outer.data);
    if (!inner) return next;
    const it = String(inner.type || "").trim();

    if (it === "koraku.trace") {
      const trace = String(inner.trace || "");
      const data = (inner.data || {}) as Record<string, unknown>;
      if (trace === "mode") {
        const mode = data.mode != null ? String(data.mode) : next.mode;
        const max =
          typeof data.max_steps === "number" ? data.max_steps : next.maxSteps;
        const model = data.model != null ? String(data.model) : next.metaModel;
        const provider =
          data.provider != null ? String(data.provider) : next.metaProvider;
        return {
          ...next,
          mode,
          maxSteps: max,
          metaModel: model || next.metaModel,
          metaProvider: provider || next.metaProvider,
          statusText: `${mode} · up to ${max} steps`,
        };
      }
      if (trace === "tools") {
        const tools = Array.isArray(data.tools)
          ? (data.tools as unknown[]).map((x) => String(x))
          : [];
        return { ...next, toolsBadges: tools };
      }
      if (trace === "tool_execution") {
        const tool = String(data.tool || "tool");
        const input = data.input;
        const callId = String(data.id || "");
        const pageTools = new Set([
          "WebPage",
          "WebFetch",
          "Firecrawl",
          "FirecrawlMap",
        ]);
        if (callId && pageTools.has(tool)) {
          const rowId = rid();
          const line = pageToolLine(tool, input, "pending");
          const pendingRow: TimelineRow = {
            id: rowId,
            kind: "tool",
            tool,
            label: line.label,
            detail: line.detail,
            ok: true,
            callId,
          };
          const meta = _metaFromSubagentPayload(data.composio_subagent);
          const withRow = _appendTimelineRow(next, pendingRow, meta);
          return {
            ...withRow,
            pendingToolByUseId: {
              ...withRow.pendingToolByUseId,
              [callId]: { tool, input, timelineRowId: rowId },
            },
            toolInvocations: withRow.toolInvocations + 1,
            statusText: `${tool}…`,
          };
        }
        const { label, detail } = humanizeToolExecution(tool, input);
        const fr = filePathFromToolInput(tool, input);
        const row: TimelineRow = {
          id: rid(),
          kind: "tool",
          tool,
          label,
          detail,
          ok: true,
          ...(fr ? { fileRelPath: fr } : {}),
        };
        const meta = _metaFromSubagentPayload(data.composio_subagent);
        const withRow = _appendTimelineRow(next, row, meta);
        return {
          ...withRow,
          toolInvocations: withRow.toolInvocations + 1,
          statusText: `${label}…`,
        };
      }
      return next;
    }

    if (it === "tool_event") {
      return handleToolEvent(next, inner);
    }

    if (it === "stream_event" && inner.event) {
      let ev: Record<string, unknown> | null = null;
      if (typeof inner.event === "string") {
        try {
          ev = JSON.parse(inner.event) as Record<string, unknown>;
        } catch {
          ev = null;
        }
      } else if (typeof inner.event === "object" && inner.event !== null) {
        ev = inner.event as Record<string, unknown>;
      }
      if (!ev) return next;
      return handleStreamEvent(next, ev);
    }

    if (it === "user" && inner.message) {
      return handleUserMessage(next, inner.message as Record<string, unknown>);
    }

    if (it === "system" && inner.subtype === "init") {
      const koraku = inner.koraku as Record<string, unknown> | undefined;
      if (koraku) {
        if (koraku.model) next = { ...next, metaModel: String(koraku.model) };
        if (koraku.provider) {
          next = { ...next, metaProvider: String(koraku.provider) };
        }
        if (koraku.mode != null && koraku.max_steps != null) {
          next = {
            ...next,
            mode: String(koraku.mode),
            maxSteps: Number(koraku.max_steps) || next.maxSteps,
            statusText: `${koraku.mode} · up to ${koraku.max_steps} steps`,
          };
        }
        const tn = koraku.tool_names;
        if (Array.isArray(tn)) {
          next = {
            ...next,
            toolsBadges: tn.map((x) => String(x)),
          };
        }
      }
      return next;
    }

    return next;
  }

  return next;
}
