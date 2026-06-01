import type { TimelineRow } from "@/lib/korakuReducer";

export type RunWorkspaceFileTouch = {
  path: string;
  tool: "Read" | "Write" | "Edit" | "Bash";
};

/** Heuristic paths to workspace files mentioned in Bash stdout/stderr (e.g. savefig, print). */
export function workspacePathsFromBashOutput(text: string): string[] {
  const raw = text.replace(/\r\n/g, "\n");
  if (!raw.trim()) return [];
  const seen = new Set<string>();
  const out: string[] = [];

  const push = (p: string) => {
    const q = p.replace(/^['"`]+|['"`]+$/g, "").trim();
    if (!q || q.includes("\n") || q.length > 220) return;
    if (/^https?:\/\//i.test(q)) return;
    if (seen.has(q)) return;
    seen.add(q);
    out.push(q);
  };

  for (const m of raw.matchAll(/savefig\s*\(\s*['"]([^'"]+)['"]/gi)) {
    push(m[1]!);
  }
  for (const m of raw.matchAll(
    /\b(?:saved|written|wrote|created)\s+(?:to|as|in)?\s+[`'"]*([\w./-]+\.(?:png|jpe?g|gif|webp|svg|pdf|csv))[`'"]*/gi,
  )) {
    push(m[1]!);
  }
  for (const m of raw.matchAll(
    /\b([\w][\w./-]{0,180}\.(?:png|jpe?g|gif|webp|svg|pdf|py|csv|json|md|txt))\b/gi,
  )) {
    push(m[1]!);
  }

  return out;
}

/**
 * Workspace-relative files from Read / Write / Edit (``fileRelPath``) plus likely artifacts
 * from successful **Bash** runs (parsed from ``outputSummary``), chronological with last touch
 * winning duplicate paths.
 */
export function collectRunWorkspaceFileTouches(
  timeline: TimelineRow[],
): RunWorkspaceFileTouch[] {
  const order = new Map<string, RunWorkspaceFileTouch["tool"]>();

  function walk(rows: TimelineRow[]) {
    for (const r of rows) {
      if (r.kind === "subagent") {
        walk(r.children);
        continue;
      }
      if (r.kind !== "tool" || r.ok === false) continue;

      if (r.tool === "Read" || r.tool === "Write" || r.tool === "Edit") {
        const p = r.fileRelPath?.trim();
        if (!p) continue;
        order.delete(p);
        order.set(p, r.tool);
        continue;
      }

      if (r.tool === "Bash" && r.outputSummary) {
        for (const p of workspacePathsFromBashOutput(r.outputSummary)) {
          order.delete(p);
          order.set(p, "Bash");
        }
      }
    }
  }

  walk(timeline);
  return [...order.entries()].map(([path, tool]) => ({ path, tool }));
}
