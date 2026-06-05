import React from "react";
import {
  Stack,
  Row,
  Grid,
  Divider,
  Table,
  Text,
  H1,
  H2,
  H3,
  Card,
  CardHeader,
  CardBody,
  Pill,
  Stat,
  Callout,
  useHostTheme,
  useCanvasState,
} from "cursor/canvas";

interface Finding {
  id: string;
  title: string;
  location: string;
  severity: "critical" | "high" | "medium" | "low";
  category: "performance" | "quality" | "optimization";
  description: string;
  snippet?: string;
  fix: string;
}

const FINDINGS: Finding[] = [
  {
    id: "redis-session-io",
    title: "Synchronous Redis session I/O inside async chat routes",
    location: "koraku/core/session_store.py (lines 126-141)",
    severity: "high",
    category: "performance",
    description: "get_or_create_chat_session() and get_session_store().save() are called directly from async chat handlers without to_thread or async Redis clients. With session_store_backend=redis, each chat turn does sync GET + JSON parse at start and sync SETEX at end, blocking the asyncio event loop for all concurrent requests.",
    snippet: `def get(self, session_id: str) -> SessionState | None:
    raw = redis_client.get(self._key(session_id))
    ...
def save(self, session: SessionState) -> None:
    payload = session.model_dump(mode="json")
    encoded = json.dumps(payload, ensure_ascii=False)
    ok = redis_client.setex(self._key(session.session_id), encoded, self._ttl_seconds())`,
    fix: "Use an async Redis client (e.g., redis.asyncio), run the sync Redis operations inside asyncio.to_thread(), or implement an async session store abstraction."
  },
  {
    id: "host-file-tools",
    title: "Host file tools block the event loop",
    location: "koraku/tools/registry.py (lines 101-108, 342-359)",
    severity: "high",
    category: "performance",
    description: "Read, Grep, Glob, Write, and Edit tools are defined as 'async def' but perform synchronous disk I/O inline. Grep is especially costly, performing a full os.walk and reading files up to 100 matches synchronously. This blocks the main event loop for all concurrent users.",
    snippet: `try:
    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    ...
    result = "".join(numbered)`,
    fix: "Wrap all local disk I/O operations (open, read, os.walk, glob) in await asyncio.to_thread() to offload them to a thread pool."
  },
  {
    id: "composio-dynamic-tools",
    title: "Composio dynamic tools rebuilt every agent turn",
    location: "koraku/agent/run.py (lines 134-141)",
    severity: "high",
    category: "performance",
    description: "On each chat turn (non-subagent mode), the agent loads Composio tools via a thread call that hits the Composio API. This is repeated for Composio subagent delegation too, leading to redundant external network requests and high latency.",
    snippet: `else:
    comp = await asyncio.to_thread(composio_runtime.build_dynamic_composio_tools)
    composio_registry_token[0] = composio_runtime.push_composio_tool_registry(comp)
    active_tools = active_tools + comp`,
    fix: "Cache the built tool lists per (user_id, toolkit_set, composio_tools_limit) with a TTL, and invalidate the cache only when connection changes are detected."
  },
  {
    id: "redis-detached-run",
    title: "Redis detached-run buffer: heavy per-SSE-chunk work",
    location: "koraku/core/detached_run_store.py (lines 227-248)",
    severity: "high",
    category: "performance",
    description: "Each streamed SSE chunk in detached mode goes through buf.append(). This runs: GET meta -> INCR -> pipeline (RPUSH, LTRIM, EXPIRE, PUBLISH) -> SET meta. A verbose agent turn with hundreds of events multiplies Redis round trips heavily.",
    snippet: `async def append(self, raw_chunk: str) -> None:
    meta = await self._load_meta()
    ...
    seq = int(await client.incr(...)) - 1
    ...
    await pipe.execute()
    ...
    await client.set(self._meta_key(), json.dumps(meta, ...), ...)`,
    fix: "Batch meta updates (e.g., update every N chunks or only on run completion), store the last_event_id in a HASH or separate key, or coalesce small chunks before appending."
  },
  {
    id: "supabase-chat-history",
    title: "Chat history hydration: two sequential Supabase queries",
    location: "koraku_cloud/integrations/supabase_chat_history.py (lines 124-142)",
    severity: "medium",
    category: "performance",
    description: "Always performs two sequential HTTP round trips on cold session hydration (first message in a thread): one to verify the thread exists, and another to fetch the messages.",
    snippet: `tr = client.get(rest_url(tq), headers=h)   # verify thread exists
...
mr = client.get(rest_url(mq), headers=h)   # fetch messages`,
    fix: "Skip the thread existence check when org_id + thread_id are already trusted from auth, or combine them into a single query/Postgres RPC view."
  },
  {
    id: "scheduler-sync",
    title: "Scheduler sync: N+1 Supabase updates",
    location: "koraku_cloud/automations/scheduler.py (lines 136-162)",
    severity: "medium",
    category: "performance",
    description: "refresh_next_run_metadata() does get_automation() + set_automation_run_times() per automation on every scheduler resync (startup, periodic resync every >=15s, and after each run). With many scheduled automations, this is an N+1 database pattern.",
    snippet: `for row in rows:
    ...
    _scheduler.add_job(...)
    refresh_next_run_metadata(uid, aid)  # get_automation + set per row`,
    fix: "Batch compute next_run_at in memory and perform a single bulk PATCH/RPC, or only refresh the metadata for the specific automation row that changed."
  },
  {
    id: "http-client-llm",
    title: "New HTTP client per LLM stream",
    location: "koraku/llm/providers/openai_compat_backend.py (line 248)",
    severity: "medium",
    category: "performance",
    description: "Every LLM call (each ReAct step) opens and closes a new AsyncClient, losing connection pooling and TLS session reuse. Same pattern in brain_graph.py line 191 (with httpx.Client() per memory-graph request).",
    snippet: `async with httpx.AsyncClient(timeout=self.timeout) as client:`,
    fix: "Use a shared, module-level httpx.AsyncClient (or sync client) with proper connection pooling."
  },
  {
    id: "broad-except",
    title: "Broad 'except Exception' with silent or minimal handling",
    location: "Multiple files (e.g., koraku/integrations/composio.py:302, koraku/agent/context_manager.py:237)",
    severity: "medium",
    category: "quality",
    description: "Using broad 'except Exception: pass' or 'except Exception as e: log.exception(e)' without proper handling or returning default values can lead to silent failures, unexpected states, or hard-to-debug behaviors.",
    snippet: `try:
    # fetch tool version or parse JSON
except Exception:
    pass`,
    fix: "Catch specific exceptions (e.g., KeyError, JSONDecodeError) and log warnings/errors where 'pass' is used, so that failures are visible and actionable."
  },
  {
    id: "in-process-state",
    title: "In-process state that does not scale across workers",
    location: "Multiple files (e.g., koraku/core/rate_limit.py, koraku_cloud/automations/webhook_guard.py)",
    severity: "medium",
    category: "quality",
    description: "Several mechanisms (rate limit fallback, webhook idempotency, automation run locks, progress throttle) use local in-memory dictionaries/sets. In a multi-worker production deployment, this state is not shared, breaking rate limits, allowing duplicate webhooks, and causing race conditions.",
    snippet: `_seen_idempotency = {} # in-memory dictionary
_run_guard = {} # in-memory run locks`,
    fix: "Store shared state in Redis (using distributed locks, Redis-backed rate limiters, and Redis SET with NX/EX for idempotency) when running in multi-worker environments."
  },
  {
    id: "ttl-cache-thread-unsafe",
    title: "TtlCache is documented thread-unsafe but used in threads",
    location: "koraku/core/ttl_cache.py (line 12)",
    severity: "medium",
    category: "quality",
    description: "TtlCache is explicitly documented as thread-unsafe, yet it is accessed from asyncio.to_thread loaders (e.g., supermemory_client, supabase_personalization, supabase_tenant). Concurrent thread access can race on OrderedDict mutations, causing crashes or corruption.",
    snippet: `"""Thread-unsafe TTL map; fine for asyncio single-process API workers."""`,
    fix: "Add a threading.Lock() around cache operations in TtlCache, or ensure the cache is only accessed from the main event loop."
  },
  {
    id: "webhook-idempotency-sorted",
    title: "Webhook idempotency prune uses sorted() (O(n log n))",
    location: "koraku_cloud/automations/webhook_guard.py (lines 22-26)",
    severity: "low",
    category: "optimization",
    description: "Under webhook bursts, the in-memory idempotency cache is pruned by sorting all items by timestamp. This is an O(n log n) operation and is highly inefficient for frequent pruning.",
    snippet: `oldest = sorted(_seen_idempotency.items(), key=lambda x: x[1])[
    : len(_seen_idempotency) - _IDEMPOTENCY_MAX_KEYS
]`,
    fix: "Use an OrderedDict (which maintains insertion order) or a heap structure (like TtlCache does) to achieve O(1) or O(log n) eviction."
  }
];

export default function CodebaseAuditCanvas() {
  const theme = useHostTheme();
  const [activeTab, setActiveTab] = useCanvasState<string>("activeTab", "overview");
  const [selectedFindingId, setSelectedFindingId] = useCanvasState<string | null>("selectedFindingId", null);

  const selectedFinding = FINDINGS.find((f) => f.id === selectedFindingId);

  const severityCounts = FINDINGS.reduce(
    (acc, f) => {
      acc[f.severity] = (acc[f.severity] || 0) + 1;
      return acc;
    },
    { critical: 0, high: 0, medium: 0, low: 0 }
  );

  const categoryCounts = FINDINGS.reduce(
    (acc, f) => {
      acc[f.category] = (acc[f.category] || 0) + 1;
      return acc;
    },
    { performance: 0, quality: 0, optimization: 0 }
  );

  const getSeverityPillTone = (severity: string) => {
    switch (severity) {
      case "critical":
        return "deleted";
      case "high":
        return "warning";
      case "medium":
        return "info";
      default:
        return "neutral";
    }
  };

  const getCategoryPillTone = (category: string) => {
    switch (category) {
      case "performance":
        return "added";
      case "quality":
        return "warning";
      default:
        return "neutral";
    }
  };

  return (
    <Stack gap={20} style={{ padding: 20, background: theme.bg.editor, minHeight: "100vh" }}>
      <Row justify="space-between" align="center">
        <Stack gap={4}>
          <H1 style={{ margin: 0 }}>Codebase Performance & Quality Audit</H1>
          <Text tone="secondary" size="small">
            Scope: `koraku` & `koraku_cloud` (excluding `web`) · Friday, Jun 5, 2026
          </Text>
        </Stack>
        <Row gap={8}>
          <Pill active={activeTab === "overview"} onClick={() => setActiveTab("overview")}>
            Overview
          </Pill>
          <Pill active={activeTab === "findings"} onClick={() => setActiveTab("findings")}>
            Findings ({FINDINGS.length})
          </Pill>
          <Pill active={activeTab === "priorities"} onClick={() => setActiveTab("priorities")}>
            Prioritized Roadmap
          </Pill>
        </Row>
      </Row>

      <Divider />

      {activeTab === "overview" && (
        <Stack gap={20}>
          <Callout tone="info" title="Executive Summary">
            The hottest paths (chat SSE, agent ReAct loop, detached runs, automations) are generally structured well: async routes, thread offloading, and TTL caches. However, several critical risks exist around **synchronous blocking on the event loop** (Redis sessions, host file tools), **per-chunk Redis work** for detached runs, **rebuilding Composio tool catalogs every turn**, and **in-process-only state** that breaks down under multi-worker deployments.
          </Callout>

          <H2>Key Metrics</H2>
          <Grid columns={4} gap={16}>
            <Stat value={FINDINGS.length.toString()} label="Total Issues Found" />
            <Stat value={severityCounts.high.toString()} label="High Severity" tone="danger" />
            <Stat value={severityCounts.medium.toString()} label="Medium Severity" tone="warning" />
            <Stat value={severityCounts.low.toString()} label="Low Severity" tone="info" />
          </Grid>

          <Grid columns={2} gap={16}>
            <Card>
              <CardHeader>Issues by Category</CardHeader>
              <CardBody>
                <Table
                  headers={["Category", "Count", "Impact"]}
                  rows={[
                    [
                      <Row gap={8} align="center">
                        <Pill active tone="deleted" size="sm">Performance</Pill>
                      </Row>,
                      categoryCounts.performance.toString(),
                      "High latency, event loop blocking, CPU spikes"
                    ],
                    [
                      <Row gap={8} align="center">
                        <Pill active tone="warning" size="sm">Code Quality</Pill>
                      </Row>,
                      categoryCounts.quality.toString(),
                      "Silent failures, thread unsafety, scaling limitations"
                    ],
                    [
                      <Row gap={8} align="center">
                        <Pill active tone="neutral" size="sm">Optimization</Pill>
                      </Row>,
                      categoryCounts.optimization.toString(),
                      "Inefficient algorithms, redundant calculations"
                    ]
                  ]}
                />
              </CardBody>
            </Card>

            <Card>
              <CardHeader>What is Done Well</CardHeader>
              <CardBody>
                <Stack gap={8}>
                  <Text size="small" weight="semibold" tone="primary">✓ Concurrency Control</Text>
                  <Text size="small" tone="secondary">Agent/tool concurrency semaphores cap parallel load safely.</Text>
                  <Text size="small" weight="semibold" tone="primary">✓ Parallel Execution</Text>
                  <Text size="small" tone="secondary">Parallel tool execution when the model emits multiple tool calls.</Text>
                  <Text size="small" weight="semibold" tone="primary">✓ Connection Pooling</Text>
                  <Text size="small" tone="secondary">Supabase HTTP connection pooling is properly configured.</Text>
                </Stack>
              </CardBody>
            </Card>
          </Grid>
        </Stack>
      )}

      {activeTab === "findings" && (
        <Grid columns="1fr 1.5fr" gap={20}>
          <Stack gap={12}>
            <H2 style={{ margin: 0 }}>Findings List</H2>
            <Stack gap={8} style={{ maxHeight: "65vh", overflowY: "auto", paddingRight: 4 }}>
              {FINDINGS.map((f) => (
                <Card
                  key={f.id}
                  style={{
                    cursor: "pointer",
                    border: selectedFindingId === f.id ? `1px solid ${theme.accent.primary}` : undefined,
                    background: selectedFindingId === f.id ? theme.fill.secondary : undefined,
                  }}
                  onClick={() => setSelectedFindingId(f.id)}
                >
                  <CardBody style={{ padding: 12 }}>
                    <Stack gap={6}>
                      <Row justify="space-between" align="center">
                        <Pill active tone={getSeverityPillTone(f.severity)} size="sm">
                          {f.severity.toUpperCase()}
                        </Pill>
                        <Pill active tone={getCategoryPillTone(f.category)} size="sm">
                          {f.category}
                        </Pill>
                      </Row>
                      <Text weight="semibold" size="small" style={{ margin: 0 }}>
                        {f.title}
                      </Text>
                      <Text tone="tertiary" size="small" truncate="start" style={{ margin: 0 }}>
                        {f.location}
                      </Text>
                    </Stack>
                  </CardBody>
                </Card>
              ))}
            </Stack>
          </Stack>

          <Stack gap={16}>
            {selectedFinding ? (
              <Card>
                <CardHeader
                  trailing={
                    <Pill active tone={getSeverityPillTone(selectedFinding.severity)}>
                      {selectedFinding.severity.toUpperCase()}
                    </Pill>
                  }
                >
                  {selectedFinding.title}
                </CardHeader>
                <CardBody>
                  <Stack gap={16}>
                    <Stack gap={4}>
                      <Text weight="semibold" size="small">Location</Text>
                      <Text tone="secondary" size="small" style={{ fontFamily: "monospace" }}>
                        {selectedFinding.location}
                      </Text>
                    </Stack>

                    <Stack gap={4}>
                      <Text weight="semibold" size="small">Description</Text>
                      <Text tone="secondary" size="small">
                        {selectedFinding.description}
                      </Text>
                    </Stack>

                    {selectedFinding.snippet && (
                      <Stack gap={4}>
                        <Text weight="semibold" size="small">Code Snippet</Text>
                        <div
                          style={{
                            background: theme.bg.chrome,
                            padding: 12,
                            borderRadius: 4,
                            fontFamily: "monospace",
                            fontSize: 11,
                            whiteSpace: "pre-wrap",
                            overflowX: "auto",
                            border: `1px solid ${theme.stroke.secondary}`,
                          }}
                        >
                          {selectedFinding.snippet}
                        </div>
                      </Stack>
                    )}

                    <Stack gap={4}>
                      <Text weight="semibold" size="small" style={{ color: theme.palette.green }}>
                        Proposed Fix
                      </Text>
                      <Text tone="secondary" size="small">
                        {selectedFinding.fix}
                      </Text>
                    </Stack>
                  </Stack>
                </CardBody>
              </Card>
            ) : (
              <Card style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <CardBody>
                  <Text tone="secondary" style={{ textAlign: "center" }}>
                    Select a finding from the list to view detailed analysis and proposed fixes.
                  </Text>
                </CardBody>
              </Card>
            )}
          </Stack>
        </Grid>
      )}

      {activeTab === "priorities" && (
        <Stack gap={20}>
          <H2>Prioritized Roadmap</H2>
          <Table
            headers={["Priority", "Task", "Impact", "Files Involved"]}
            rows={[
              [
                <Pill active tone="deleted">P0 - CRITICAL</Pill>,
                <Stack gap={2}>
                  <Text weight="semibold" size="small">Async Redis Session I/O</Text>
                  <Text tone="secondary" size="small">Offload synchronous Redis calls in chat routes to avoid event loop blocking.</Text>
                </Stack>,
                "Unblocks the event loop for all concurrent chat turns, preventing major latency spikes.",
                "koraku/core/session_store.py"
              ],
              [
                <Pill active tone="deleted">P0 - CRITICAL</Pill>,
                <Stack gap={2}>
                  <Text weight="semibold" size="small">Thread Offloading for Host File Tools</Text>
                  <Text tone="secondary" size="small">Wrap Read, Grep, Glob, Write, and Edit tools in asyncio.to_thread().</Text>
                </Stack>,
                "Prevents multi-tenant latency spikes and event loop starvation from synchronous disk operations.",
                "koraku/tools/registry.py"
              ],
              [
                <Pill active tone="warning">P1 - HIGH</Pill>,
                <Stack gap={2}>
                  <Text weight="semibold" size="small">Cache Composio Built Tools</Text>
                  <Text tone="secondary" size="small">Cache dynamic tools per user/TTL instead of rebuilding on every single turn.</Text>
                </Stack>,
                "Drastically cuts external API calls and CPU overhead on each chat turn.",
                "koraku/agent/run.py"
              ],
              [
                <Pill active tone="warning">P1 - HIGH</Pill>,
                <Stack gap={2}>
                  <Text weight="semibold" size="small">Optimize Redis Detached-Run Buffer</Text>
                  <Text tone="secondary" size="small">Batch metadata updates and reduce Redis operations per SSE chunk.</Text>
                </Stack>,
                "Improves streaming scalability and reduces Redis load significantly under high traffic.",
                "koraku/core/detached_run_store.py"
              ],
              [
                <Pill active tone="info">P2 - MEDIUM</Pill>,
                <Stack gap={2}>
                  <Text weight="semibold" size="small">Redis-Backed Webhook Idempotency</Text>
                  <Text tone="secondary" size="small">Move in-memory webhook guard and rate limiters to Redis.</Text>
                </Stack>,
                "Ensures correct rate limiting and webhook deduplication in multi-worker environments.",
                "koraku_cloud/automations/webhook_guard.py"
              ],
              [
                <Pill active tone="neutral">P3 - LOW</Pill>,
                <Stack gap={2}>
                  <Text weight="semibold" size="small">Cleanup Dead Code & Deduplicate</Text>
                  <Text tone="secondary" size="small">Remove unused markers in run.py and deduplicate present.py enrichment.</Text>
                </Stack>,
                "Improves codebase maintainability and readability.",
                "koraku/agent/run.py, present.py"
              ]
            ]}
          />
        </Stack>
      )}
    </Stack>
  );
}
