import { describe, expect, it } from "vitest";
import {
  applyKorakuSseEvent,
  initialRunState,
  type RunState,
} from "./korakuReducer";

const SUBAGENT = { composio: true, toolkits: ["GMAIL"] };

function streamSubagentText(s: RunState, text: string): RunState {
  let next = s;
  next = applyKorakuSseEvent(next, {
    type: "koraku.subagent",
    data: { phase: "composio_start", toolkits: ["GMAIL"] },
  });
  for (const ch of text.split("")) {
    next = applyKorakuSseEvent(next, {
      type: "koraku.event",
      data: {
        type: "stream_event",
        event: {
          type: "content_block_delta",
          index: 0,
          delta: { type: "text_delta", text: ch },
          subagent: SUBAGENT,
        },
      },
    });
  }
  return next;
}

function thoughtBodies(s: RunState): string[] {
  const nest = s.timeline.find((r) => r.kind === "subagent");
  if (!nest || nest.kind !== "subagent") return [];
  return nest.children
    .filter((c) => c.kind === "thought")
    .map((c) => (c.kind === "thought" ? c.body : ""));
}

describe("Composio subagent prose streaming", () => {
  it("accumulates text deltas into one thought row, not one per chunk", () => {
    const s0 = initialRunState();
    const s1 = streamSubagentText(s0, "Search results (1 email)");
    const bodies = thoughtBodies(s1);
    expect(bodies).toHaveLength(0);
    expect(s1.activeThought?.text).toBe("Search results (1 email)");

    const s2 = applyKorakuSseEvent(s1, {
      type: "koraku.subagent",
      data: { phase: "composio_end", toolkits: ["GMAIL"] },
    });
    const bodiesAfter = thoughtBodies(s2);
    expect(bodiesAfter).toHaveLength(1);
    expect(bodiesAfter[0]).toBe("Search results (1 email)");
    expect(s2.activeThought).toBeNull();
  });

  it("finalizes subagent prose on text content_block_stop", () => {
    let s = initialRunState();
    s = applyKorakuSseEvent(s, {
      type: "koraku.subagent",
      data: { phase: "composio_start", toolkits: ["GMAIL"] },
    });
    s = applyKorakuSseEvent(s, {
      type: "koraku.event",
      data: {
        type: "stream_event",
        event: {
          type: "content_block_start",
          index: 0,
          content_block: { type: "text", text: "" },
          subagent: SUBAGENT,
        },
      },
    });
    s = applyKorakuSseEvent(s, {
      type: "koraku.event",
      data: {
        type: "stream_event",
        event: {
          type: "content_block_delta",
          index: 0,
          delta: { type: "text_delta", text: "Done" },
          subagent: SUBAGENT,
        },
      },
    });
    s = applyKorakuSseEvent(s, {
      type: "koraku.event",
      data: {
        type: "stream_event",
        event: { type: "content_block_stop", index: 0, subagent: SUBAGENT },
      },
    });
    expect(thoughtBodies(s)).toEqual(["Done"]);
    expect(s.activeThought).toBeNull();
  });
});
