"use client";

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import clsx from "clsx";
import {
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  FileText,
  Folder,
  Loader2,
  PanelRightClose,
  RefreshCw,
} from "lucide-react";
import { MarkdownBody } from "@/components/MarkdownBody";
import { korakuFetch } from "@/lib/koraku-fetch";
import { sanitizeHtml } from "@/lib/sanitize-html";

// mammoth (~200KB+) is only needed when a .docx file is previewed; load lazily
// so it doesn't ship in the chat-page client bundle.
async function convertDocxToHtml(buf: ArrayBuffer): Promise<string> {
  const { default: mammoth } = await import("mammoth");
  const conv = await mammoth.convertToHtml({ arrayBuffer: buf });
  return sanitizeHtml(conv.value);
}

const LS_PANEL_W = "koraku.workspace.panelWidthPx";
const LS_TREE_W = "koraku.workspace.treeWidthPx";
const LS_TREE_COLLAPSED = "koraku.workspace.treeCollapsed";

const PANEL_MIN = 300;
const PANEL_DEFAULT = 560;
const TREE_MIN = 112;
const TREE_DEFAULT = 200;
const TREE_MAX_FIXED = 440;

function clamp(n: number, lo: number, hi: number) {
  return Math.min(hi, Math.max(lo, n));
}

function readNumLs(key: string, fallback: number) {
  if (typeof window === "undefined") return fallback;
  const raw = localStorage.getItem(key);
  const n = raw ? parseInt(raw, 10) : NaN;
  return Number.isFinite(n) ? n : fallback;
}

function readBoolLs(key: string, fallback: boolean) {
  if (typeof window === "undefined") return fallback;
  const raw = localStorage.getItem(key);
  if (raw === "1" || raw === "true") return true;
  if (raw === "0" || raw === "false") return false;
  return fallback;
}

type TreeEntry = {
  name: string;
  path: string;
};

type TreeResponse = {
  root: string;
  path: string;
  files: TreeEntry[];
  directories: TreeEntry[];
};

type FilePreview =
  | { kind: "markdown"; path: string; content: string; truncated: boolean }
  | { kind: "text"; path: string; content: string; truncated: boolean }
  | { kind: "pdf"; path: string; blobUrl: string }
  | { kind: "image"; path: string; blobUrl: string }
  | { kind: "docx"; path: string; html: string };

function joinRel(parent: string, name: string): string {
  const p = parent.trim();
  const n = name.trim();
  if (!p) return n;
  if (!n) return p;
  return `${p}/${n}`;
}

function extensionOf(rel: string): string {
  const base = rel.split("/").pop() ?? rel;
  const i = base.lastIndexOf(".");
  return i >= 0 ? base.slice(i).toLowerCase() : "";
}

function isMarkdownExt(ext: string): boolean {
  return ext === ".md" || ext === ".markdown" || ext === ".mdx";
}

const IMAGE_EXT_MIME: Record<string, string> = {
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".jpe": "image/jpeg",
  ".gif": "image/gif",
  ".webp": "image/webp",
  ".avif": "image/avif",
  ".bmp": "image/bmp",
  ".ico": "image/x-icon",
  ".tif": "image/tiff",
  ".tiff": "image/tiff",
  ".svg": "image/svg+xml",
  ".heic": "image/heic",
  ".heif": "image/heif",
  ".jfif": "image/jpeg",
  ".apng": "image/apng",
};

function isImageExt(ext: string): boolean {
  return Boolean(ext && IMAGE_EXT_MIME[ext]);
}

function imageMimeType(ext: string): string {
  return IMAGE_EXT_MIME[ext] ?? "application/octet-stream";
}

function isTextLikeExt(ext: string): boolean {
  if (!ext) return true;
  const text = new Set([
    ".txt",
    ".log",
    ".csv",
    ".tsv",
    ".json",
    ".jsonl",
    ".ndjson",
    ".tsx",
    ".ts",
    ".mts",
    ".cts",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".xml",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".env",
    ".sh",
    ".bash",
    ".zsh",
    ".py",
    ".rs",
    ".go",
    ".java",
    ".kt",
    ".swift",
    ".rb",
    ".php",
    ".sql",
    ".graphql",
    ".vue",
    ".svelte",
    ".dockerfile",
    ".gitignore",
    ".mdc",
  ]);
  return text.has(ext);
}

function fileBaseName(rel: string): string {
  const parts = rel.split("/").filter(Boolean);
  return parts[parts.length - 1] ?? rel;
}

/**
 * Cloud workspace column — docks to the right of chat (same chrome idea as ``Sidebar``),
 * not a modal overlay.
 */
export function WorkspacePanel({
  visible,
  onClose,
  serverSessionId,
  workspaceRefreshToken = 0,
}: {
  visible: boolean;
  onClose: () => void;
  serverSessionId: string | null;
  workspaceRefreshToken?: number;
}) {
  const innerSplitRef = useRef<HTMLDivElement>(null);

  const [panelWidthPx, setPanelWidthPx] = useState(PANEL_DEFAULT);
  const [treeWidthPx, setTreeWidthPx] = useState(TREE_DEFAULT);
  const [treeCollapsed, setTreeCollapsed] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const [resizeMode, setResizeMode] = useState<null | "panel" | "tree">(null);

  const [relPath, setRelPath] = useState("");
  const [tree, setTree] = useState<TreeResponse | null>(null);
  const [fileRel, setFileRel] = useState<string | null>(null);
  const [filePreview, setFilePreview] = useState<FilePreview | null>(null);
  const [loadingTree, setLoadingTree] = useState(false);
  const [loadingFile, setLoadingFile] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useLayoutEffect(() => {
    setPanelWidthPx(clamp(readNumLs(LS_PANEL_W, PANEL_DEFAULT), PANEL_MIN, 2000));
    setTreeWidthPx(clamp(readNumLs(LS_TREE_W, TREE_DEFAULT), TREE_MIN, TREE_MAX_FIXED));
    setTreeCollapsed(readBoolLs(LS_TREE_COLLAPSED, false));
    setHydrated(true);
  }, []);

  const maxPanelWidth = useCallback(() => {
    if (typeof window === "undefined") return 900;
    return clamp(window.innerWidth - 320, PANEL_MIN, 1200);
  }, []);

  const maxTreeWidth = useCallback(() => {
    const el = innerSplitRef.current;
    const inner = el?.clientWidth ?? 400;
    return clamp(Math.floor(inner * 0.62), TREE_MIN, TREE_MAX_FIXED);
  }, []);

  const startPanelResize = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      setResizeMode("panel");
      const startX = e.clientX;
      const startW = panelWidthPx;
      const onMove = (ev: MouseEvent) => {
        // Handle is on the panel's left edge: drag left widens, drag right narrows.
        const next = clamp(
          Math.round(startW + startX - ev.clientX),
          PANEL_MIN,
          maxPanelWidth(),
        );
        setPanelWidthPx(next);
      };
      const onUp = () => {
        setResizeMode(null);
        window.removeEventListener("mousemove", onMove);
        window.removeEventListener("mouseup", onUp);
        setPanelWidthPx((w) => {
          localStorage.setItem(LS_PANEL_W, String(w));
          return w;
        });
      };
      window.addEventListener("mousemove", onMove);
      window.addEventListener("mouseup", onUp);
    },
    [maxPanelWidth, panelWidthPx],
  );

  const startTreeResize = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      if (treeCollapsed) return;
      setResizeMode("tree");
      const startX = e.clientX;
      const startW = treeWidthPx;
      const onMove = (ev: MouseEvent) => {
        const next = clamp(
          Math.round(startW + ev.clientX - startX),
          TREE_MIN,
          maxTreeWidth(),
        );
        setTreeWidthPx(next);
      };
      const onUp = () => {
        setResizeMode(null);
        window.removeEventListener("mousemove", onMove);
        window.removeEventListener("mouseup", onUp);
        setTreeWidthPx((w) => {
          localStorage.setItem(LS_TREE_W, String(w));
          return w;
        });
      };
      window.addEventListener("mousemove", onMove);
      window.addEventListener("mouseup", onUp);
    },
    [maxTreeWidth, treeCollapsed, treeWidthPx],
  );

  const collapseTree = useCallback(() => {
    setTreeCollapsed(true);
    localStorage.setItem(LS_TREE_COLLAPSED, "1");
  }, []);

  const expandTree = useCallback(() => {
    setTreeCollapsed(false);
    localStorage.setItem(LS_TREE_COLLAPSED, "0");
  }, []);

  useEffect(() => {
    if (!visible) return;
    const onResize = () => {
      setPanelWidthPx((w) => clamp(w, PANEL_MIN, maxPanelWidth()));
      setTreeWidthPx((tw) => clamp(tw, TREE_MIN, maxTreeWidth()));
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [visible, maxPanelWidth, maxTreeWidth]);

  const loadTree = useCallback(async () => {
    if (!serverSessionId) return;
    setLoadingTree(true);
    setError(null);
    try {
      const q = new URLSearchParams({
        session_id: serverSessionId,
        path: relPath,
      });
      const res = await korakuFetch(`/koraku-api/api/workspace/tree?${q}`);
      const text = await res.text();
      if (!res.ok) {
        setTree(null);
        setError(text.slice(0, 400) || res.statusText);
        return;
      }
      setTree(JSON.parse(text) as TreeResponse);
    } catch (e) {
      setTree(null);
      setError(String((e as Error)?.message || e));
    } finally {
      setLoadingTree(false);
    }
  }, [relPath, serverSessionId]);

  const loadFile = useCallback(
    async (rel: string) => {
      if (!serverSessionId) return;
      setLoadingFile(true);
      setError(null);
      setFileRel(rel);
      setFilePreview(null);
      const ext = extensionOf(rel);
      try {
        if (ext === ".pdf" || ext === ".docx" || isImageExt(ext)) {
          const q = new URLSearchParams({
            session_id: serverSessionId,
            path: rel,
          });
          const res = await korakuFetch(`/koraku-api/api/workspace/file/blob?${q}`);
          if (!res.ok) {
            const t = await res.text();
            setError(t.slice(0, 400) || res.statusText);
            return;
          }
          const buf = await res.arrayBuffer();
          if (ext === ".pdf") {
            const blob = new Blob([buf], { type: "application/pdf" });
            const blobUrl = URL.createObjectURL(blob);
            setFilePreview({ kind: "pdf", path: rel, blobUrl });
          } else if (ext === ".docx") {
            const html = await convertDocxToHtml(buf);
            setFilePreview({ kind: "docx", path: rel, html });
          } else {
            const blob = new Blob([buf], { type: imageMimeType(ext) });
            const blobUrl = URL.createObjectURL(blob);
            setFilePreview({ kind: "image", path: rel, blobUrl });
          }
          return;
        }

        const q = new URLSearchParams({
          session_id: serverSessionId,
          path: rel,
        });
        const res = await korakuFetch(`/koraku-api/api/workspace/file?${q}`);
        const text = await res.text();
        if (!res.ok) {
          setError(text.slice(0, 400) || res.statusText);
          return;
        }
        const data = JSON.parse(text) as {
          path: string;
          content: string;
          truncated: boolean;
        };
        const kind = isMarkdownExt(ext) ? "markdown" : "text";
        setFilePreview({
          kind,
          path: data.path,
          content: data.content,
          truncated: data.truncated,
        });
      } catch (e) {
        setError(String((e as Error)?.message || e));
      } finally {
        setLoadingFile(false);
      }
    },
    [serverSessionId],
  );

  useEffect(() => {
    if (!filePreview) return;
    if (filePreview.kind !== "pdf" && filePreview.kind !== "image") return;
    const u = filePreview.blobUrl;
    return () => URL.revokeObjectURL(u);
  }, [filePreview]);

  useEffect(() => {
    if (visible) {
      setRelPath("");
      setFileRel(null);
      setFilePreview(null);
      setError(null);
    }
  }, [visible]);

  useEffect(() => {
    if (!visible || !serverSessionId) return;
    void loadTree();
  }, [visible, serverSessionId, relPath, loadTree, workspaceRefreshToken]);

  const segments = relPath ? relPath.split("/").filter(Boolean) : [];

  const panelW = hydrated ? panelWidthPx : PANEL_DEFAULT;

  return (
    <aside
      style={{ width: visible ? panelW : 0 }}
      className={clsx(
        "relative flex h-full min-h-0 shrink-0 flex-col overflow-hidden rounded-[28px] border border-neutral-200/90 bg-[#f7f7f7] ease-out",
        "shadow-[0_0_0_3px_rgb(255_255_255),0_0_0_4px_rgb(229_229_229_/_0.55),0_14px_40px_-14px_rgb(0_0_0_/_0.09)]",
        resizeMode === "panel" ? "duration-0" : "duration-200 transition-[width]",
        visible ? "min-w-[300px]" : "min-w-0 border-transparent shadow-none",
      )}
      aria-hidden={!visible}
    >
      {visible ? (
        <button
          type="button"
          aria-label="Resize workspace panel"
          onMouseDown={startPanelResize}
          className={clsx(
            "absolute left-0 top-0 z-20 h-full w-3 -translate-x-1/2 cursor-col-resize touch-none",
            "bg-transparent hover:bg-neutral-900/[0.06] active:bg-neutral-900/[0.1]",
            resizeMode === "panel" && "bg-neutral-900/10",
          )}
        />
      ) : null}
      <div
        className={clsx(
          "flex h-full min-h-0 w-full flex-col",
          visible ? "min-w-[300px]" : "min-w-0",
          !visible && "pointer-events-none opacity-0",
        )}
      >
        <header className="flex h-9 shrink-0 items-center justify-between gap-2 border-b border-neutral-200/70 bg-neutral-100/90 px-2.5">
          <span className="truncate text-[11px] font-bold uppercase tracking-[0.12em] text-neutral-500">
            Workspace
          </span>
          <div className="flex shrink-0 items-center gap-0.5">
            <button
              type="button"
              onClick={() => void loadTree()}
              disabled={!serverSessionId || loadingTree}
              className="flex h-7 w-7 items-center justify-center rounded-md text-neutral-500 transition hover:bg-white/80 hover:text-neutral-900 disabled:opacity-40"
              title="Refresh explorer"
            >
              <RefreshCw
                className={clsx("h-3.5 w-3.5", loadingTree && "animate-spin")}
                strokeWidth={1.5}
              />
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex h-7 w-7 items-center justify-center rounded-md text-neutral-500 transition hover:bg-white/80 hover:text-neutral-900"
              title="Close workspace"
            >
              <PanelRightClose className="h-3.5 w-3.5" strokeWidth={1.5} />
            </button>
          </div>
        </header>

        {!serverSessionId ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-2 px-5 text-center text-[13px] text-neutral-500">
            <p>Send a message in chat first.</p>
            <p className="text-xs text-neutral-400">
              Your Koraku workspace folder appears here after the first reply streams.
            </p>
          </div>
        ) : (
          <>
            <div ref={innerSplitRef} className="flex min-h-0 flex-1 flex-row overflow-hidden">
              {treeCollapsed ? (
                <div className="flex w-9 shrink-0 flex-col items-center border-r border-neutral-200/70 bg-neutral-100/60 py-2">
                  <button
                    type="button"
                    onClick={expandTree}
                    title="Show explorer"
                    className="rounded-md p-1.5 text-neutral-500 transition hover:bg-white/90 hover:text-neutral-900"
                  >
                    <ChevronsRight className="h-4 w-4" strokeWidth={1.5} aria-hidden />
                  </button>
                </div>
              ) : (
                <>
                  <div
                    style={{ width: treeWidthPx }}
                    className="flex min-h-0 min-w-0 shrink-0 flex-col border-r border-neutral-200/70 bg-neutral-100/50"
                  >
                    <div className="flex h-8 shrink-0 items-center justify-between border-b border-neutral-200/60 px-2">
                      <span className="text-[10px] font-bold uppercase tracking-[0.14em] text-neutral-500">
                        Explorer
                      </span>
                      <button
                        type="button"
                        onClick={collapseTree}
                        title="Hide explorer"
                        className="rounded p-1 text-neutral-400 transition hover:bg-white/70 hover:text-neutral-700"
                      >
                        <ChevronsLeft className="h-3.5 w-3.5" strokeWidth={1.5} aria-hidden />
                      </button>
                    </div>

                    <nav
                      aria-label="Folder path"
                      className="flex shrink-0 items-center gap-0.5 overflow-x-auto border-b border-neutral-200/50 px-2 py-1.5 text-[10px] text-neutral-500"
                    >
                      <button
                        type="button"
                        className="shrink-0 rounded px-1 py-0.5 font-medium transition hover:bg-white/80 hover:text-neutral-800"
                        onClick={() => {
                          setRelPath("");
                          setFileRel(null);
                          setFilePreview(null);
                        }}
                      >
                        workspace
                      </button>
                      {segments.map((seg, i) => {
                        const cum = segments.slice(0, i + 1).join("/");
                        return (
                          <span key={cum} className="flex shrink-0 items-center">
                            <ChevronRight className="mx-0.5 h-3 w-3 opacity-40" aria-hidden />
                            <button
                              type="button"
                              className="max-w-[7rem] truncate rounded px-1 py-0.5 transition hover:bg-white/80 hover:text-neutral-800"
                              onClick={() => {
                                setRelPath(cum);
                                setFileRel(null);
                                setFilePreview(null);
                              }}
                            >
                              {seg}
                            </button>
                          </span>
                        );
                      })}
                    </nav>

                    {error && !tree ? (
                      <p className="p-2 text-xs text-red-600">{error}</p>
                    ) : null}

                    <ul className="min-h-0 flex-1 overflow-y-auto py-0.5">
                      {relPath ? (
                        <li>
                          <button
                            type="button"
                            className="flex w-full items-center gap-2 px-2 py-1 text-left text-[12px] text-neutral-600 transition hover:bg-white/60"
                            onClick={() => {
                              const parts = relPath.split("/").filter(Boolean);
                              parts.pop();
                              setRelPath(parts.join("/"));
                              setFileRel(null);
                              setFilePreview(null);
                            }}
                          >
                            <span className="text-neutral-400">‥</span>
                            <span>..</span>
                          </button>
                        </li>
                      ) : null}
                      {(tree?.directories ?? []).map((d) => (
                        <li key={`d:${d.path}`}>
                          <button
                            type="button"
                            className="flex w-full items-center gap-1.5 px-2 py-[3px] text-left text-[12px] transition hover:bg-white/60"
                            onClick={() => {
                              setRelPath(joinRel(relPath, d.name));
                              setFileRel(null);
                              setFilePreview(null);
                            }}
                          >
                            <Folder className="h-3.5 w-3.5 shrink-0 text-amber-600/90" />
                            <span className="truncate text-koraku-ink">{d.name}</span>
                          </button>
                        </li>
                      ))}
                      {(tree?.files ?? []).map((f) => {
                        const full = joinRel(relPath, f.name);
                        const ext = extensionOf(f.name);
                        const previewable =
                          ext === ".pdf" ||
                          ext === ".docx" ||
                          isImageExt(ext) ||
                          isMarkdownExt(ext) ||
                          isTextLikeExt(ext);
                        const active = fileRel === full;
                        return (
                          <li key={`f:${f.path}`}>
                            <button
                              type="button"
                              className={clsx(
                                "flex w-full items-center gap-1.5 border-l-2 px-2 py-[3px] text-left text-[12px] transition",
                                active
                                  ? "border-orange-600 bg-white/90 text-neutral-900"
                                  : "border-transparent hover:bg-white/60",
                                !previewable && "opacity-50",
                              )}
                              title={
                                previewable
                                  ? undefined
                                  : "No in-panel preview for this type yet"
                              }
                              onClick={() =>
                                previewable ? void loadFile(full) : undefined
                              }
                              disabled={!previewable}
                            >
                              <FileText className="h-3.5 w-3.5 shrink-0 text-neutral-400" />
                              <span className="truncate">{f.name}</span>
                            </button>
                          </li>
                        );
                      })}
                      {!loadingTree &&
                      !(tree?.directories?.length) &&
                      !(tree?.files?.length) ? (
                        <li className="px-3 py-6 text-center text-[11px] text-neutral-400">
                          Empty folder
                        </li>
                      ) : null}
                      {loadingTree ? (
                        <li className="flex items-center justify-center gap-2 py-8 text-[11px] text-neutral-400">
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          Loading…
                        </li>
                      ) : null}
                    </ul>
                  </div>

                  <div
                    role="separator"
                    aria-orientation="vertical"
                    aria-label="Resize explorer"
                    onMouseDown={startTreeResize}
                    className={clsx(
                      "group relative z-10 w-1 shrink-0 cursor-col-resize touch-none bg-neutral-200/40",
                      resizeMode === "tree" && "bg-neutral-300",
                    )}
                  >
                    <div className="pointer-events-none absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-neutral-200/80 group-hover:bg-neutral-300" />
                  </div>
                </>
              )}

              <div className="flex min-h-0 min-w-0 flex-1 flex-col bg-white">
                <div className="flex h-9 shrink-0 items-end gap-px overflow-x-auto border-b border-neutral-200/70 bg-neutral-100/40 px-1 pt-1">
                  {fileRel ? (
                    <div
                      className="flex h-8 max-w-full items-center gap-2 rounded-t-md border border-b-0 border-neutral-200/80 bg-white px-3 text-[12px] font-medium text-koraku-ink shadow-sm"
                      title={fileRel}
                    >
                      <FileText className="h-3.5 w-3.5 shrink-0 text-neutral-400" />
                      <span className="truncate">{fileBaseName(fileRel)}</span>
                    </div>
                  ) : (
                    <span className="px-2 pb-2 text-[11px] font-medium text-neutral-400">
                      No file open
                    </span>
                  )}
                </div>

                {error && tree ? (
                  <p className="shrink-0 border-b border-red-100 bg-red-50 px-3 py-1.5 text-xs text-red-700">
                    {error}
                  </p>
                ) : null}

                {!fileRel ? (
                  <p className="m-auto max-w-[14rem] text-center text-[11px] leading-relaxed text-neutral-400">
                    Select a file from the explorer to preview it here.
                  </p>
                ) : loadingFile ? (
                  <div className="m-auto flex items-center gap-2 text-xs text-neutral-400">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Loading…
                  </div>
                ) : filePreview ? (
                  <div className="flex min-h-0 flex-1 flex-col">
                    {"truncated" in filePreview && filePreview.truncated ? (
                      <p className="shrink-0 border-b border-amber-100 bg-amber-50/90 px-3 py-1 text-[10px] font-medium text-amber-800">
                        Preview truncated — open in chat or download for the full file.
                      </p>
                    ) : null}
                    {filePreview.kind === "markdown" ? (
                      <div className="koraku-md min-h-0 flex-1 overflow-auto px-4 py-3">
                        <MarkdownBody source={filePreview.content} />
                      </div>
                    ) : null}
                    {filePreview.kind === "text" ? (
                      <pre className="min-h-0 flex-1 overflow-auto bg-neutral-50/50 p-3 font-mono text-[11px] leading-relaxed text-neutral-800">
                        {filePreview.content}
                      </pre>
                    ) : null}
                    {filePreview.kind === "pdf" ? (
                      <iframe
                        title="PDF preview"
                        src={filePreview.blobUrl}
                        className="min-h-0 w-full flex-1 border-0 bg-neutral-100"
                      />
                    ) : null}
                    {filePreview.kind === "image" ? (
                      <div className="flex min-h-0 flex-1 items-start justify-center overflow-auto bg-neutral-50 p-3">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={filePreview.blobUrl}
                          alt=""
                          className="max-h-[min(85dvh,48rem)] max-w-full object-contain shadow-sm ring-1 ring-neutral-200/60"
                        />
                      </div>
                    ) : null}
                    {filePreview.kind === "docx" ? (
                      <div
                        className="koraku-md min-h-0 flex-1 overflow-auto break-words px-4 py-3 text-[13px] leading-relaxed text-neutral-800"
                        dangerouslySetInnerHTML={{ __html: filePreview.html }}
                      />
                    ) : null}
                  </div>
                ) : null}
              </div>
            </div>

            <footer className="flex h-6 shrink-0 items-center border-t border-neutral-200/70 bg-koraku-ink px-2.5 text-[10px] font-medium text-white/90">
              <span className="min-w-0 truncate">
                {fileRel ?? (relPath ? relPath : "workspace")}
              </span>
            </footer>
          </>
        )}
      </div>
    </aside>
  );
}
