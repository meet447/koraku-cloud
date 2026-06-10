/** Human-readable tool timeline lines — never JSON.stringify. */

function s(v: unknown): string | undefined {
  if (typeof v !== "string") return undefined;
  const t = v.trim();
  return t ? t : undefined;
}

function trunc(t: string, max: number): string {
  if (t.length <= max) return t;
  return `${t.slice(0, max - 1)}…`;
}

/** Show URL in full when short; otherwise middle-ellipsis for very long URLs. */
export function formatUrlForTimeline(raw: string, max = 100): string {
  const u = raw.trim();
  if (u.length <= max) return u;
  const head = Math.ceil(max * 0.55);
  const tail = max - head - 1;
  return `${u.slice(0, head)}…${u.slice(-tail)}`;
}

function pickFirst(
  o: Record<string, unknown>,
  keys: string[],
): string | undefined {
  for (const k of keys) {
    const v = s(o[k]);
    if (v) return v;
  }
  return undefined;
}

const VERB: Record<string, string> = {
  Read: "Read file",
  Write: "Wrote file",
  Edit: "Edited file",
  Bash: "Shell command",
  Glob: "Matched files",
  Grep: "Searched in files",
  TodoWrite: "Updated tasks",
  WebSearch: "Web search",
  WebPage: "Opened page",
  WebFetch: "Fetched page",
  Firecrawl: "Scraped page",
  FirecrawlMap: "Mapped site",
  ExaSearch: "Web search",
  ComposioRun: "Connected apps",
  ResearchRun: "Research worker",
  CodeRun: "Code worker",
  ParallelRun: "Parallel workers",
  VerifyGoal: "Verify goal",
  DocumentRun: "Document worker",
  PresentationRun: "Presentation worker",
  SpreadsheetRun: "Spreadsheet worker",
  PdfRun: "PDF worker",
};

function fallbackLabel(tool: string): string {
  return VERB[tool] ?? `Ran ${tool}`;
}

export type PagePhase = "pending" | "done" | "error";

export type ToolPhase = "pending" | "done";

/** Labels for WebPage / WebFetch / Firecrawl / FirecrawlMap rows (including pending). */
export function pageToolLine(
  tool: string,
  input: unknown,
  phase: PagePhase,
): { label: string; detail?: string } {
  const o =
    input && typeof input === "object" ? (input as Record<string, unknown>) : {};
  const url = s(o.url);
  const detail = url ? formatUrlForTimeline(url) : undefined;
  if (phase === "pending") {
    return { label: "Loading page", detail };
  }
  if (phase === "error") {
    return { label: "Page failed to load", detail };
  }
  if (tool === "FirecrawlMap") {
    return { label: "Mapped links from site", detail };
  }
  if (tool === "Firecrawl") {
    return { label: "Scraped page", detail };
  }
  return { label: tool === "WebPage" ? "Opened page" : "Fetched page", detail };
}

/**
 * One line for `tool_execution` trace (non-page tools, or when not using pending row).
 */
/** Workspace-relative path from Read / Write / Edit tool input (for downloads). */
export function filePathFromToolInput(tool: string, input: unknown): string | undefined {
  if (tool !== "Read" && tool !== "Write" && tool !== "Edit") return undefined;
  if (!input || typeof input !== "object") return undefined;
  const o = input as Record<string, unknown>;
  const fp = s(o.file_path);
  if (fp) return fp;
  const p = s(o.path);
  return p;
}

export function humanizeToolExecution(
  tool: string,
  input: unknown,
  phase: ToolPhase = "done",
): { label: string; detail?: string } {
  const pending = phase === "pending";
  if (!input || typeof input !== "object") {
    if (pending) {
      if (tool === "Read") return { label: "Reading file" };
      if (tool === "Write") return { label: "Writing file" };
      if (tool === "Edit") return { label: "Editing file" };
      if (tool === "Bash") return { label: "Running shell command" };
      if (tool === "WebSearch") return { label: "Searching the web" };
      if (tool === "ComposioRun") return { label: "Using connected apps" };
    }
    return { label: fallbackLabel(tool) };
  }
  const o = input as Record<string, unknown>;

  switch (tool) {
    case "WebSearch": {
      const q = s(o.query);
      return q
        ? {
            label: pending ? "Searching the web" : "Web search",
            detail: trunc(q, 140),
          }
        : { label: pending ? "Searching the web" : "Web search" };
    }
    case "ExaSearch": {
      const q = s(o.query);
      return q
        ? {
            label: pending ? "Searching the web" : "Web search",
            detail: trunc(q, 140),
          }
        : { label: pending ? "Searching the web" : "Web search" };
    }
    case "Glob": {
      const pattern = s(o.pattern) ?? "*";
      const path = s(o.path) ?? ".";
      return {
        label: "Matched files",
        detail: trunc(`${pattern} · ${path}`, 160),
      };
    }
    case "Grep": {
      const pattern = s(o.pattern) ?? "";
      const path = s(o.path) ?? ".";
      const inc = s(o.include);
      const parts: string[] = [];
      if (pattern) parts.push(trunc(pattern, 100));
      if (path && path !== ".") parts.push(path);
      if (inc && inc !== "*") parts.push(`files: ${inc}`);
      return {
        label: "Searched in files",
        detail: parts.length ? parts.join(" · ") : undefined,
      };
    }
    case "Read": {
      const path = s(o.file_path) ?? s(o.path);
      return path
        ? {
            label: pending ? "Reading file" : "Read file",
            detail: trunc(path, 160),
          }
        : { label: pending ? "Reading file" : "Read file" };
    }
    case "Write": {
      const path = s(o.file_path) ?? s(o.path);
      return path
        ? {
            label: pending ? "Writing file" : "Wrote file",
            detail: trunc(path, 160),
          }
        : { label: pending ? "Writing file" : "Wrote file" };
    }
    case "Edit": {
      const path = s(o.file_path) ?? s(o.path);
      return path
        ? {
            label: pending ? "Editing file" : "Edited file",
            detail: trunc(path, 160),
          }
        : { label: pending ? "Editing file" : "Edited file" };
    }
    case "Bash": {
      const cmd = s(o.command);
      return cmd
        ? {
            label: pending ? "Running shell command" : "Shell command",
            detail: trunc(cmd, 140),
          }
        : { label: pending ? "Running shell command" : "Shell command" };
    }
    case "TodoWrite": {
      const todos = o.todos;
      const n = Array.isArray(todos) ? todos.length : 0;
      return {
        label: "Updated tasks",
        detail: n > 0 ? `${n} item${n === 1 ? "" : "s"}` : undefined,
      };
    }
    case "WebPage":
    case "WebFetch":
    case "Firecrawl":
    case "FirecrawlMap": {
      const url = s(o.url);
      return url
        ? { label: fallbackLabel(tool), detail: formatUrlForTimeline(url) }
        : { label: fallbackLabel(tool) };
    }
    case "ComposioRun":
    case "ResearchRun":
    case "CodeRun":
    case "ParallelRun":
    case "DocumentRun":
    case "PresentationRun":
    case "SpreadsheetRun":
    case "PdfRun":
    case "VerifyGoal": {
      const goal = s(o.goal) ?? s(o.criteria);
      const label = VERB[tool] ?? fallbackLabel(tool);
      return goal
        ? {
            label: pending ? label : label,
            detail: trunc(goal, 140),
          }
        : { label };
    }
    default: {
      const hit = pickFirst(o, [
        "url",
        "href",
        "query",
        "prompt",
        "path",
        "pattern",
        "command",
        "file_path",
        "target_file",
        "extract_prompt",
      ]);
      if (hit) return { label: fallbackLabel(tool), detail: trunc(hit, 160) };
      return { label: fallbackLabel(tool) };
    }
  }
}

/** Turn noisy tool_result errors into a short line (no JSON dumps). */
export function humanizeToolErrorSnippet(text: string, max = 220): string {
  let t = text.replace(/\s+/g, " ").trim();
  if (t.startsWith("Error:")) t = t.slice(6).trim();
  const url = t.match(/https?:\/\/[^\s]+/);
  if (url && t.length > max) {
    const withoutLongJson = t.replace(/\{[\s\S]{20,}\}/g, " ").replace(/\s+/g, " ").trim();
    if (withoutLongJson.length < t.length) {
      return trunc(withoutLongJson, max);
    }
  }
  if (t.startsWith("{") && t.includes('"')) {
    try {
      const j = JSON.parse(t) as { message?: string; error?: string };
      const m = s(j.message) ?? s(j.error);
      if (m) return trunc(m, max);
    } catch {
      /* ignore */
    }
  }
  return trunc(t, max);
}
