import { describe, expect, it } from "vitest";
import {
  applyKorakuSseEvent,
  initialRunState,
  type RunState,
} from "./korakuReducer";

const RESEARCH_SUBAGENT = { workhorse: "research" };

function workhorseToolBodies(s: RunState): string[] {
  const nest = s.timeline.find(
    (r) => r.kind === "subagent" && r.variant === "workhorse",
  );
  if (!nest || nest.kind !== "subagent") return [];
  return nest.children
    .filter((c) => c.kind === "tool")
    .map((c) => (c.kind === "tool" ? c.label : ""));
}

describe("Parallel subagent nesting", () => {
  it("nests ParallelRun delegate row under parallel batch on parallel_start", () => {
    let s = initialRunState();
    s = applyKorakuSseEvent(s, {
      type: "koraku.event",
      data: {
        type: "tool_event",
        phase: "started",
        tool_use_id: "pr-1",
        tool_name: "ParallelRun",
        tool_input: { tasks: [{ kind: "document", goal: "doc" }] },
      },
    });
    expect(s.timeline.some((r) => r.kind === "tool" && r.tool === "ParallelRun")).toBe(true);

    s = applyKorakuSseEvent(s, {
      type: "koraku.subagent",
      data: { phase: "parallel_start", count: 3 },
    });
    const parallel = s.timeline.find(
      (r) => r.kind === "subagent" && r.variant === "parallel",
    );
    expect(parallel?.kind).toBe("subagent");
    if (parallel?.kind !== "subagent") return;
    expect(s.timeline.some((r) => r.kind === "tool" && r.tool === "ParallelRun")).toBe(false);
    expect(
      parallel.children.some((c) => c.kind === "tool" && c.tool === "ParallelRun"),
    ).toBe(true);
  });

  it("routes tools to the matching worker nest, not the innermost open nest", () => {
    let s = initialRunState();
    s = applyKorakuSseEvent(s, {
      type: "koraku.subagent",
      data: { phase: "parallel_start", count: 2 },
    });
    s = applyKorakuSseEvent(s, {
      type: "koraku.subagent",
      data: { phase: "workhorse_start", workhorse: "research" },
    });
    s = applyKorakuSseEvent(s, {
      type: "koraku.subagent",
      data: { phase: "workhorse_start", workhorse: "code" },
    });
    s = applyKorakuSseEvent(s, {
      type: "koraku.event",
      data: {
        type: "tool_event",
        phase: "started",
        tool_use_id: "code-1",
        tool_name: "Bash",
        tool_input: { command: "python chart.py" },
        subagent: { workhorse: "code" },
      },
    });
    const parallel = s.timeline.find(
      (r) => r.kind === "subagent" && r.variant === "parallel",
    );
    expect(parallel?.kind).toBe("subagent");
    if (parallel?.kind !== "subagent") return;
    const codeNest = parallel.children.find(
      (c) => c.kind === "subagent" && c.variant === "workhorse" && c.worker === "code",
    );
    expect(codeNest?.kind).toBe("subagent");
    if (codeNest?.kind !== "subagent") return;
    expect(codeNest.children.some((c) => c.kind === "tool" && c.tool === "Bash")).toBe(true);
    const researchNest = parallel.children.find(
      (c) => c.kind === "subagent" && c.variant === "workhorse" && c.worker === "research",
    );
    if (researchNest?.kind === "subagent") {
      expect(researchNest.children.some((c) => c.kind === "tool")).toBe(false);
    }
  });
});

describe("Workhorse subagent nesting", () => {
  it("opens a research worker group and nests tool rows", () => {
    let s = initialRunState();
    s = applyKorakuSseEvent(s, {
      type: "koraku.subagent",
      data: { phase: "workhorse_start", workhorse: "research" },
    });
    s = applyKorakuSseEvent(s, {
      type: "koraku.event",
      data: {
        type: "tool_event",
        phase: "started",
        tool_use_id: "wh-1",
        tool_name: "WebSearch",
        tool_input: { query: "nifty 50" },
        subagent: RESEARCH_SUBAGENT,
      },
    });
    const nest = s.timeline.find((r) => r.kind === "subagent");
    expect(nest?.kind).toBe("subagent");
    if (nest?.kind === "subagent") {
      expect(nest.variant).toBe("workhorse");
      expect(nest.worker).toBe("research");
      expect(nest.open).toBe(true);
      expect(nest.children.some((c) => c.kind === "tool")).toBe(true);
    }
    expect(workhorseToolBodies(s).some((l) => /search/i.test(l))).toBe(true);

    s = applyKorakuSseEvent(s, {
      type: "koraku.subagent",
      data: { phase: "workhorse_end", workhorse: "research" },
    });
    const closed = s.timeline.find((r) => r.kind === "subagent");
    if (closed?.kind === "subagent") {
      expect(closed.open).toBe(false);
    }
  });

  it("shows parallel batch with nested workers", () => {
    let s = initialRunState();
    s = applyKorakuSseEvent(s, {
      type: "koraku.subagent",
      data: { phase: "parallel_start", count: 2 },
    });
    s = applyKorakuSseEvent(s, {
      type: "koraku.subagent",
      data: { phase: "workhorse_start", workhorse: "research" },
    });
    s = applyKorakuSseEvent(s, {
      type: "koraku.subagent",
      data: { phase: "workhorse_end", workhorse: "research" },
    });
    s = applyKorakuSseEvent(s, {
      type: "koraku.subagent",
      data: { phase: "parallel_end", count: 2 },
    });
    const parallel = s.timeline.find(
      (r) => r.kind === "subagent" && r.variant === "parallel",
    );
    expect(parallel?.kind).toBe("subagent");
    if (parallel?.kind === "subagent") {
      expect(parallel.open).toBe(false);
      expect(parallel.children.some((c) => c.kind === "subagent")).toBe(true);
    }
  });
});

describe("Thought nesting in subagents", () => {
  it("keeps thinking inside the worker when finalized after workhorse_end", () => {
    let s = initialRunState();
    s = applyKorakuSseEvent(s, {
      type: "koraku.subagent",
      data: { phase: "workhorse_start", workhorse: "presentation" },
    });
    s = applyKorakuSseEvent(s, {
      type: "koraku.event",
      data: {
        type: "stream_event",
        event: {
          type: "content_block_start",
          index: 0,
          content_block: { type: "thinking" },
          subagent: { workhorse: "presentation" },
        },
      },
    });
    for (const ch of "Slide 5: sector cards\nSlide 6: bullets".split("")) {
      s = applyKorakuSseEvent(s, {
        type: "koraku.event",
        data: {
          type: "stream_event",
          event: {
            type: "content_block_delta",
            index: 0,
            delta: { type: "thinking_delta", thinking: ch },
            subagent: { workhorse: "presentation" },
          },
        },
      });
    }
    s = applyKorakuSseEvent(s, {
      type: "koraku.subagent",
      data: { phase: "workhorse_end", workhorse: "presentation" },
    });
    s = applyKorakuSseEvent(s, {
      type: "koraku.event",
      data: {
        type: "stream_event",
        event: {
          type: "content_block_stop",
          index: 0,
          subagent: { workhorse: "presentation" },
        },
      },
    });
    const nest = s.timeline.find(
      (r) => r.kind === "subagent" && r.variant === "workhorse" && r.worker === "presentation",
    );
    expect(nest?.kind).toBe("subagent");
    if (nest?.kind !== "subagent") return;
    expect(nest.children.some((c) => c.kind === "thought" && /Slide 5/i.test(c.body))).toBe(
      true,
    );
    expect(s.timeline.some((r) => r.kind === "thought")).toBe(false);
  });

  it("does not assign presentation thinking to a later code message_start", () => {
    let s = initialRunState();
    s = applyKorakuSseEvent(s, {
      type: "koraku.subagent",
      data: { phase: "workhorse_start", workhorse: "presentation" },
    });
    s = applyKorakuSseEvent(s, {
      type: "koraku.event",
      data: {
        type: "stream_event",
        event: {
          type: "content_block_delta",
          index: 0,
          delta: {
            type: "thinking_delta",
            thinking:
              "Planning deck layout for sectors with cards on slide five and bullet lists on slide six",
          },
          subagent: { workhorse: "presentation" },
        },
      },
    });
    s = applyKorakuSseEvent(s, {
      type: "koraku.event",
      data: {
        type: "stream_event",
        event: { type: "message_start", subagent: { workhorse: "code" } },
      },
    });
    const pres = s.timeline.find(
      (r) => r.kind === "subagent" && r.worker === "presentation",
    );
    expect(pres?.kind).toBe("subagent");
    if (pres?.kind !== "subagent") return;
    expect(
      pres.children.some((c) => c.kind === "thought" && /Planning deck/i.test(c.body)),
    ).toBe(true);
    expect(s.timeline.some((r) => r.kind === "thought")).toBe(false);
  });
});

describe("Thought coalescing", () => {
  it("drops tiny thoughts across react steps instead of one row per chunk", () => {
    let s = initialRunState();
    const tiny = "The";
    s = applyKorakuSseEvent(s, {
      type: "koraku.event",
      data: {
        type: "stream_event",
        event: {
          type: "content_block_start",
          index: 0,
          content_block: { type: "thinking" },
        },
      },
    });
    for (const ch of tiny) {
      s = applyKorakuSseEvent(s, {
        type: "koraku.event",
        data: {
          type: "stream_event",
          event: {
            type: "content_block_delta",
            index: 0,
            delta: { type: "thinking_delta", thinking: ch },
          },
        },
      });
    }
    s = applyKorakuSseEvent(s, {
      type: "koraku.event",
      data: {
        type: "stream_event",
        event: { type: "content_block_stop", index: 0 },
      },
    });
    s = applyKorakuSseEvent(s, {
      type: "koraku.event",
      data: {
        type: "stream_event",
        event: { type: "message_start" },
      },
    });
    expect(s.timeline.filter((r) => r.kind === "thought")).toHaveLength(0);
  });
});
