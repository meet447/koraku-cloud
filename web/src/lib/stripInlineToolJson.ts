/**
 * Removes inline tool-call JSON blobs from assistant text (defense in depth when
 * the Python stream filter is off or a provider shape slips through).
 */
const TOOL_JSON_START = /\{\s*"tool"\s*:\s*"/;

/** Legacy transcripts that used tagged “thinking” blocks — strip stray markup. */
const LEGACY_KORAKU_THINKING = /<koraku_thinking>[\s\S]*?<\/koraku_thinking>|<\/?koraku_thinking>/gi;

/** Some models emit empty ``[TOOL_CALL] [/TOOL_CALL]`` training artifacts in the answer channel. */
const BRACKET_TOOL_CALL_SPAN = /\[\s*TOOL_CALL\s*\][\s\S]*?\[\s*\/\s*TOOL_CALL\s*\]/gi;

function stripBracketToolCallSpans(s: string): string {
  for (let guard = 0; guard < 64; guard++) {
    const next = s.replace(BRACKET_TOOL_CALL_SPAN, "");
    if (next === s) break;
    s = next;
  }
  return s;
}

/** Names emitted by the compact OpenAI tool line: `Ran WebPage {...}`. */
const COMPACT_TOOL_NAMES = new Set([
  "WebPage",
  "WebSearch",
  "Read",
  "Write",
  "Edit",
  "Bash",
  "Glob",
  "Grep",
  "TodoWrite",
  "WebFetch",
  "Firecrawl",
  "FirecrawlMap",
  "ExaSearch",
  "Task",
  "TaskOutput",
]);

function tryParseJsonObjectAt(
  s: string,
  start: number,
): { obj: unknown; end: number } | null {
  if (start >= s.length || s[start] !== "{") return null;
  let depth = 0;
  let inStr = false;
  let esc = false;
  for (let i = start; i < s.length; i++) {
    const c = s[i];
    if (inStr) {
      if (esc) {
        esc = false;
      } else if (c === "\\") {
        esc = true;
      } else if (c === '"') {
        inStr = false;
      }
      continue;
    }
    if (c === '"') {
      inStr = true;
      continue;
    }
    if (c === "{") depth++;
    if (c === "}") {
      depth--;
      if (depth === 0) {
        const chunk = s.slice(start, i + 1);
        try {
          return { obj: JSON.parse(chunk), end: i + 1 };
        } catch {
          return null;
        }
      }
    }
  }
  return null;
}

function isToolCallObject(obj: unknown): boolean {
  return (
    !!obj &&
    typeof obj === "object" &&
    typeof (obj as { tool?: unknown }).tool === "string"
  );
}

function stripCallToolBlobs(s: string): string {
  let i = 0;
  let out = "";
  const lower = s.toLowerCase();
  while (i < s.length) {
    const idx = lower.indexOf("[call ", i);
    if (idx === -1) {
      out += s.slice(i);
      break;
    }
    out += s.slice(i, idx);
    const tail = s.slice(idx);
    const m = /^\[Call\s+[A-Za-z][A-Za-z0-9_]*\]\s*:\s*/i.exec(tail);
    if (!m) {
      out += s[idx] ?? "";
      i = idx + 1;
      continue;
    }
    let jsonStart = m[0].length;
    while (jsonStart < tail.length && /\s/.test(tail[jsonStart]!)) jsonStart++;
    const parsed = tryParseJsonObjectAt(tail, jsonStart);
    if (
      parsed &&
      typeof parsed.obj === "object" &&
      parsed.obj !== null &&
      !Array.isArray(parsed.obj)
    ) {
      // Strips both `{"tool":"…"}` compact calls and native args like `{"url":"…"}`.
      i = idx + parsed.end;
      continue;
    }
    out += s.slice(idx, idx + m[0].length);
    i = idx + m[0].length;
  }
  return out;
}

function stripRanToolBlobs(s: string): string {
  let i = 0;
  let out = "";
  const lower = s.toLowerCase();
  while (i < s.length) {
    const idx = lower.indexOf("ran ", i);
    if (idx === -1) {
      out += s.slice(i);
      break;
    }
    if (idx > 0 && /[A-Za-z0-9_/]/.test(s[idx - 1]!)) {
      out += s.slice(i, idx + 4);
      i = idx + 4;
      continue;
    }
    out += s.slice(i, idx);
    const tail = s.slice(idx);
    const m = /^Ran\s+([A-Za-z][A-Za-z0-9_]*)\s+/i.exec(tail);
    if (!m) {
      out += s[idx] ?? "";
      i = idx + 1;
      continue;
    }
    const toolName = m[1] ?? "";
    if (!COMPACT_TOOL_NAMES.has(toolName)) {
      out += s.slice(idx, idx + m[0].length);
      i = idx + m[0].length;
      continue;
    }
    const jsonStart = idx + m[0].length;
    const parsed = tryParseJsonObjectAt(s, jsonStart);
    if (
      parsed &&
      typeof parsed.obj === "object" &&
      parsed.obj !== null &&
      !Array.isArray(parsed.obj)
    ) {
      i = parsed.end;
      continue;
    }
    out += s.slice(idx, idx + m[0].length);
    i = idx + m[0].length;
  }
  return out;
}

export function stripInlineToolJsonFromAnswer(text: string): string {
  let s = text.replace(LEGACY_KORAKU_THINKING, "");
  s = stripBracketToolCallSpans(s);
  s = stripCallToolBlobs(s);
  s = stripRanToolBlobs(s);
  for (let guard = 0; guard < 64; guard++) {
    const m = TOOL_JSON_START.exec(s);
    if (!m || m.index === undefined) break;
    const parsed = tryParseJsonObjectAt(s, m.index);
    if (!parsed || !isToolCallObject(parsed.obj)) break;
    s = s.slice(0, m.index) + s.slice(parsed.end);
  }
  return s;
}
