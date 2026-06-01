"use client";

import { useEffect, useMemo, useState } from "react";
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
  children: React.ReactNode;
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

function TreeRow({ children }: { children: React.ReactNode }) {
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
  const [expanded, setExpanded] = useState(true);
  const open = expanded;

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
        <span className="font-semibold text-koraku-ink">
          {live ? "Thinking" : `Thought for ${seconds.toFixed(1)}s`}
          {live ? (
            <span className="font-medium text-neutral-400">
              {" "}
              · {seconds.toFixed(1)}s
            </span>
          ) : null}
        </span>
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

function SubagentGroup({
  row,
}: {
  row: Extract<TimelineRow, { kind: "subagent" }>;
}) {
  const [open, setOpen] = useState(true);
  const tk = row.toolkits.length ? row.toolkits.join(", ") : "integrations";
  const label = row.open
    ? `Integration worker · ${tk}`
    : `Integration worker · ${tk} (done)`;
  return (
    <div className="text-[13px] leading-snug">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-start gap-2 text-left"
      >
        <span className="mt-0.5 shrink-0 text-neutral-500">
          {open ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </span>
        <Layers2 className="mt-0.5 h-4 w-4 shrink-0 text-violet-500" aria-hidden />
        <span className="font-semibold text-koraku-ink">{label}</span>
      </button>
      {open ? (
        <div className="mt-2 space-y-4 border-l border-violet-200/80 pl-3 ml-[1.125rem]">
          {row.children.length === 0 ? (
            <p className="text-[12px] text-neutral-400">Working…</p>
          ) : (
            row.children.map((child) => (
              <div key={child.id}>
                {child.kind === "thought" ? (
                  <ThoughtBlock
                    seconds={child.seconds}
                    body={child.body}
                  />
                ) : child.kind === "subagent" ? (
                  <SubagentGroup row={child} />
                ) : (
                  <ToolLine row={child} />
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
  return (
    <div className="text-[13px] leading-snug">
      <div className="flex gap-2.5">
        <Icon
          className={clsx(
            "mt-0.5 h-4 w-4 shrink-0",
            failed ? "text-red-500" : "text-neutral-400",
          )}
        />
        <div className="min-w-0 flex-1">
          <p
            className={clsx(
              "font-medium text-neutral-700",
              failed && "text-red-700",
            )}
          >
            <span>{row.label}</span>
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

export function ToolTimeline({
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
  const [cardOpen, setCardOpen] = useState(false);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (streamingExpand) setCardOpen(true);
  }, [streamingExpand]);

  useEffect(() => {
    if (!streamingExpand) setCardOpen(false);
  }, [streamingExpand]);

  useEffect(() => {
    if (!activeThought) return;
    const t = window.setInterval(() => setTick((x) => x + 1), 500);
    return () => clearInterval(t);
  }, [activeThought]);

  const liveThoughtSeconds = useMemo(() => {
    if (!activeThought) return 0;
    void tick;
    return Math.max(0, (Date.now() - activeThought.started) / 1000);
  }, [activeThought, tick]);

  const nTools = toolCallCount;
  const hasTree =
    rows.length > 0 || activeThought != null || nTools > 0;

  if (!hasTree) return null;

  const header =
    nTools > 0
      ? `Called ${nTools} tool${nTools === 1 ? "" : "s"}`
      : "Agent activity";

  const entries: { key: string; node: React.ReactNode }[] = [];

  rows.forEach((row) => {
    if (row.kind === "thought") {
      entries.push({
        key: row.id,
        node: <ThoughtBlock seconds={row.seconds} body={row.body} />,
      });
    } else if (row.kind === "subagent") {
      entries.push({
        key: row.id,
        node: <SubagentGroup row={row} />,
      });
    } else {
      entries.push({
        key: row.id,
        node: <ToolLine row={row} />,
      });
    }
  });

  if (activeThought) {
    entries.push({
      key: "__live_thought__",
      node: (
        <ThoughtBlock
          seconds={Math.round(liveThoughtSeconds * 10) / 10}
          body={activeThought.text}
          live
        />
      ),
    });
  }

  return (
    <div className="mb-6 bg-transparent px-0 py-1">
      <button
        type="button"
        onClick={() => setCardOpen((o) => !o)}
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
        <TreeRows hasItems={entries.length > 0}>
          {entries.map((e) => (
            <TreeRow key={e.key}>{e.node}</TreeRow>
          ))}
        </TreeRows>
      )}
    </div>
  );
}
