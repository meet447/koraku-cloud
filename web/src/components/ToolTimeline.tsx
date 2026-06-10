"use client";

import { memo, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  AlertCircle,
  Brain,
  ChevronDown,
  ChevronRight,
  Code2,
  FileText,
  Globe2,
  Layers2,
  Search,
  TerminalSquare,
} from "lucide-react";
import clsx from "clsx";
import type { RunState, TimelineRow } from "@/lib/korakuReducer";
import { KORAKU_COPY } from "@/lib/korakuBrand";

function iconFor(row: TimelineRow) {
  if (row.kind === "thought") return Brain;
  if (row.kind === "subagent") return Layers2;
  if (row.kind === "tool" && row.ok === false) return AlertCircle;
  const t = row.tool;
  if (t === "WebSearch" || t === "ExaSearch") return Search;
  if (t === "WebFetch" || t === "Firecrawl" || t === "FirecrawlMap") {
    return Globe2;
  }
  if (t === "Bash" || t === "Glob" || t === "Grep") return TerminalSquare;
  if (t === "Read" || t === "Write" || t === "Edit") return FileText;
  return Code2;
}

function TreeRows({
  children,
  hasItems,
}: {
  children: ReactNode;
  hasItems: boolean;
}) {
  if (!hasItems) return null;
  return (
    <div className="relative mt-3 pl-1">
      <div
        className="absolute bottom-3 left-[13px] top-2 w-px bg-neutral-200"
        aria-hidden
      />
      <ul className="relative m-0 list-none space-y-0 p-0">{children}</ul>
    </div>
  );
}

function TreeRow({ children }: { children: ReactNode }) {
  return (
    <li className="relative m-0 pb-5 pl-10 last:pb-1">
      <div
        className="absolute left-[13px] top-[11px] h-px w-[14px] bg-neutral-200"
        aria-hidden
      />
      <div className="relative">{children}</div>
    </li>
  );
}

function ThoughtBlock({
  seconds,
  body,
  live,
}: {
  seconds: number;
  body: string;
  live?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const open = expanded;
  const header = live
    ? `Thinking · ${seconds.toFixed(1)}s`
    : `Thought for ${seconds.toFixed(1)}s`;

  return (
    <div className="text-[13px] leading-snug">
      <button
        type="button"
        onClick={() => setExpanded((e) => !e)}
        className="flex w-full items-start gap-1.5 text-left"
      >
        <span className="mt-0.5 shrink-0 text-neutral-500">
          {open ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </span>
        <span className="font-semibold text-koraku-ink">{header}</span>
      </button>
      {open ? (
        <p
          className={clsx(
            "mt-2 max-h-64 overflow-y-auto whitespace-pre-wrap pl-[1.375rem] text-[13px] font-normal text-neutral-600",
            live && "border-l border-neutral-100 pl-3",
          )}
        >
          {body || (live ? "…" : "")}
        </p>
      ) : null}
    </div>
  );
}

const MemoThoughtBlock = memo(ThoughtBlock);

function DetailText({
  text,
  failed,
}: {
  text: string;
  failed: boolean;
}) {
  const isUrl = /^https?:\/\//i.test(text.trim());
  if (isUrl) {
    const href = text.trim();
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className={clsx(
          "break-all font-normal text-koraku-accent underline decoration-koraku-accent/30 underline-offset-2 hover:decoration-koraku-accent",
          failed && "text-red-700 decoration-red-300",
        )}
      >
        {text}
      </a>
    );
  }
  return (
    <span
      className={clsx(
        "font-normal text-neutral-500",
        failed && "text-red-600/90",
      )}
    >
      {text}
    </span>
  );
}

const WORKER_LABELS: Record<string, string> = {
  research: KORAKU_COPY.researchWorker,
  code: KORAKU_COPY.codeWorker,
  document: "Document worker",
  presentation: "Presentation worker",
  spreadsheet: "Spreadsheet worker",
  pdf: "PDF worker",
};

function subagentGroupLabel(
  row: Extract<TimelineRow, { kind: "subagent" }>,
): string {
  if (row.variant === "workhorse") {
    const w = WORKER_LABELS[row.worker || ""] || row.worker || "Worker";
    return row.open ? w : `${w} (done)`;
  }
  if (row.variant === "parallel") {
    const n = row.parallelCount || Math.max(1, row.children.length);
    const base = `${KORAKU_COPY.parallelWorkers} · ${n}`;
    return row.open ? base : `${base} (done)`;
  }
  const tk = row.toolkits.length ? row.toolkits.join(", ") : "integrations";
  return row.open
    ? `${KORAKU_COPY.connectedAppsWorker} · ${tk}`
    : `${KORAKU_COPY.connectedAppsWorker} · ${tk} (done)`;
}

function SubagentGroup({
  row,
}: {
  row: Extract<TimelineRow, { kind: "subagent" }>;
}) {
  const [userOpen, setUserOpen] = useState<boolean | null>(null);
  const open = userOpen ?? row.open;
  const label = subagentGroupLabel(row);
  const accent =
    row.variant === "workhorse"
      ? "text-sky-500"
      : row.variant === "parallel"
        ? "text-amber-600"
        : "text-violet-500";
  const border =
    row.variant === "workhorse"
      ? "border-sky-200/80"
      : row.variant === "parallel"
        ? "border-amber-200/80"
        : "border-violet-200/80";
  return (
    <div className="text-[13px] leading-snug">
      <button
        type="button"
        onClick={() => setUserOpen((o) => !(o ?? row.open))}
        className="flex w-full items-start gap-2 text-left"
      >
        <span className="mt-0.5 shrink-0 text-neutral-500">
          {open ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </span>
        <Layers2 className={`mt-0.5 h-4 w-4 shrink-0 ${accent}`} aria-hidden />
        <span className="font-semibold text-koraku-ink">{label}</span>
      </button>
      {open ? (
        <div className={`mt-2 space-y-4 border-l ${border} pl-3 ml-[1.125rem]`}>
          {row.children.length === 0 ? (
            <p className="text-[12px] text-neutral-400">Working…</p>
          ) : (
            row.children.map((child) => (
              <div key={child.id}>
                {child.kind === "thought" ? (
                  <MemoThoughtBlock
                    seconds={child.seconds}
                    body={child.body}
                  />
                ) : child.kind === "subagent" ? (
                  <MemoSubagentGroup row={child} />
                ) : (
                  <MemoToolLine row={child} />
                )}
              </div>
            ))
          )}
        </div>
      ) : null}
    </div>
  );
}

function ToolLine({ row }: { row: Extract<TimelineRow, { kind: "tool" }> }) {
  const Icon = iconFor(row);
  const failed = row.ok === false;
  const running = Boolean(row.callId);
  return (
    <div className="text-[13px] leading-snug">
      <div className="flex gap-2.5">
        {running ? (
          <span
            className="mt-0.5 inline-flex h-4 w-4 shrink-0 items-center justify-center"
            aria-hidden
          >
            <span className="inline-flex h-2 w-2 animate-pulse rounded-full bg-koraku-accent" />
          </span>
        ) : (
          <Icon
            className={clsx(
              "mt-0.5 h-4 w-4 shrink-0",
              failed ? "text-red-500" : "text-neutral-400",
            )}
          />
        )}
        <div className="min-w-0 flex-1">
          <p
            className={clsx(
              "font-medium",
              failed ? "text-red-700" : running ? "text-koraku-ink" : "text-neutral-700",
            )}
          >
            <span>
              {row.label}
              {running ? "…" : null}
            </span>
            {row.detail ? (
              <>
                <br />
                <DetailText text={row.detail} failed={failed} />
              </>
            ) : null}
          </p>
        </div>
      </div>
    </div>
  );
}

const MemoToolLine = memo(
  ToolLine,
  (prev, next) =>
    prev.row === next.row ||
    (prev.row.id === next.row.id &&
      prev.row.label === next.row.label &&
      prev.row.detail === next.row.detail &&
      prev.row.ok === next.row.ok &&
      prev.row.callId === next.row.callId),
);

/** Timer isolated so the full trace tree does not re-render every 500ms. */
function LiveThoughtBlock({
  started,
  body,
}: {
  started: number;
  body: string;
}) {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const t = window.setInterval(() => setTick((x) => x + 1), 500);
    return () => clearInterval(t);
  }, []);
  const seconds = useMemo(() => {
    void tick;
    return Math.round(Math.max(0, (Date.now() - started) / 1000) * 10) / 10;
  }, [started, tick]);
  return <ThoughtBlock seconds={seconds} body={body} live />;
}

function hasRunningToolInTimeline(rows: TimelineRow[]): boolean {
  for (const row of rows) {
    if (row.kind === "tool" && row.callId) return true;
    if (row.kind === "subagent" && hasRunningToolInTimeline(row.children)) {
      return true;
    }
  }
  return false;
}

const MemoSubagentGroup = memo(
  SubagentGroup,
  (prev, next) =>
    prev.row === next.row ||
    (prev.row.id === next.row.id &&
      prev.row.open === next.row.open &&
      prev.row.children === next.row.children),
);

function timelineRowNode(row: TimelineRow): ReactNode {
  if (row.kind === "thought") {
    return <MemoThoughtBlock seconds={row.seconds} body={row.body} />;
  }
  if (row.kind === "subagent") {
    return <MemoSubagentGroup row={row} />;
  }
  return <MemoToolLine row={row} />;
}

function ToolTimelineInner({
  rows,
  activeThought,
  toolCallCount,
  streamingExpand = false,
}: {
  rows: TimelineRow[];
  activeThought: RunState["activeThought"];
  toolCallCount: number;
  /** While true (live last assistant turn), expand details; collapse when the turn finishes. */
  streamingExpand?: boolean;
}) {
  const [manualCardOpen, setManualCardOpen] = useState<boolean | null>(null);
  const cardOpen = manualCardOpen ?? streamingExpand;

  const hasRunningTool = useMemo(
    () => hasRunningToolInTimeline(rows),
    [rows],
  );
  const hasTree = rows.length > 0 || activeThought != null || toolCallCount > 0;

  const header = useMemo(() => {
    if (hasRunningTool) return "Running tools";
    if (toolCallCount > 0) {
      return `Called ${toolCallCount} tool${toolCallCount === 1 ? "" : "s"}`;
    }
    return "Agent activity";
  }, [hasRunningTool, toolCallCount]);

  const rowEntries = useMemo(
    () =>
      rows.map((row) => ({
        key: row.id,
        node: timelineRowNode(row),
      })),
    [rows],
  );

  const showLiveThought = activeThought != null;

  if (!hasTree) return null;

  return (
    <div className="mb-6 bg-transparent px-0 py-1">
      <button
        type="button"
        onClick={() => setManualCardOpen((o) => !(o ?? streamingExpand))}
        className="flex w-full items-center gap-2 text-left text-sm font-bold tracking-tight text-koraku-ink"
      >
        {cardOpen ? (
          <ChevronDown className="h-4 w-4 shrink-0 text-neutral-500" />
        ) : (
          <ChevronRight className="h-4 w-4 shrink-0 text-neutral-500" />
        )}
        <span>{header}</span>
      </button>

      {cardOpen && (
        <TreeRows hasItems={rowEntries.length > 0 || showLiveThought}>
          {rowEntries.map((e) => (
            <TreeRow key={e.key}>{e.node}</TreeRow>
          ))}
          {showLiveThought && activeThought ? (
            <TreeRow key="__live_thought__">
              <LiveThoughtBlock
                started={activeThought.started}
                body={activeThought.text}
              />
            </TreeRow>
          ) : null}
        </TreeRows>
      )}
    </div>
  );
}

function toolTimelinePropsEqual(
  prev: {
    rows: TimelineRow[];
    activeThought: RunState["activeThought"];
    toolCallCount: number;
    streamingExpand?: boolean;
  },
  next: {
    rows: TimelineRow[];
    activeThought: RunState["activeThought"];
    toolCallCount: number;
    streamingExpand?: boolean;
  },
): boolean {
  return (
    prev.rows === next.rows &&
    prev.toolCallCount === next.toolCallCount &&
    prev.streamingExpand === next.streamingExpand &&
    prev.activeThought === next.activeThought
  );
}

export const ToolTimeline = memo(ToolTimelineInner, toolTimelinePropsEqual);
