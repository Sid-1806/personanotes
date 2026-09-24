"use client";

import { AlertTriangle, Maximize2, Minus, Plus, RotateCcw, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

interface MermaidApi {
  initialize: (config: Record<string, unknown>) => void;
  render: (id: string, chart: string) => Promise<{ svg: string }>;
}

// Lazy-load mermaid only when a diagram is actually rendered (it's a large dep).
// The specifier is cast to string so tsc doesn't require mermaid's type
// declarations; the bundler still resolves the literal "mermaid" at runtime.
let mermaidLoader: Promise<{ default: MermaidApi }> | null = null;
function loadMermaid() {
  if (!mermaidLoader) {
    mermaidLoader = import("mermaid" as string) as Promise<{ default: MermaidApi }>;
  }
  return mermaidLoader;
}

const MIN_ZOOM = 0.5;
const MAX_ZOOM = 3;

/**
 * Renders a Mermaid block, with zoom and a fullscreen view.
 *
 * A diagram at phone width is unreadable without zoom, and an invalid diagram
 * used to collapse silently to raw code with no explanation — so a failure now
 * says what happened and offers a way to fix it.
 */
export function MermaidDiagram({
  chart,
  onFix,
}: {
  chart: string;
  /** Hook for "ask AI to fix this diagram" — a targeted refine. */
  onFix?: (chart: string) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    let active = true;
    setFailed(false);
    setSvg(null);

    loadMermaid()
      .then(async (mod) => {
        const mermaid = mod.default;
        mermaid.initialize({
          startOnLoad: false,
          theme: "dark",
          securityLevel: "strict",
          fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif",
        });
        const id = "mmd-" + Math.random().toString(36).slice(2);
        const { svg: rendered } = await mermaid.render(id, chart);
        if (active) setSvg(rendered);
      })
      .catch(() => {
        if (active) setFailed(true);
      });

    return () => {
      active = false;
    };
  }, [chart]);

  useEffect(() => {
    if (!expanded) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setExpanded(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [expanded]);

  const adjustZoom = useCallback((delta: number) => {
    setZoom((current) => Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, Number((current + delta).toFixed(2)))));
  }, []);

  if (failed) {
    return (
      <div className="mb-4 overflow-hidden rounded-lg border border-amber-500/30 bg-amber-500/5">
        <div className="flex flex-wrap items-center gap-2 border-b border-amber-500/20 px-3 py-2 text-sm text-amber-300">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span className="flex-1">This diagram couldn&apos;t be drawn — the syntax is invalid.</span>
          {onFix && (
            <button
              type="button"
              onClick={() => onFix(chart)}
              className="rounded-md border border-amber-500/30 px-2 py-1 text-xs font-medium text-amber-200 hover:bg-amber-500/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-400"
            >
              Ask AI to fix it
            </button>
          )}
        </div>
        <pre className="overflow-x-auto p-4 text-xs text-slate-300">{chart}</pre>
      </div>
    );
  }

  if (!svg) {
    return (
      <div className="mb-4 h-40 animate-pulse rounded-lg border border-slate-800 bg-slate-900/60" />
    );
  }

  const diagram = (
    <div
      ref={ref}
      className="mermaid-diagram flex min-w-full justify-center"
      style={{ transform: `scale(${zoom})`, transformOrigin: "center top" }}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );

  return (
    <>
      <figure className="mb-4 overflow-hidden rounded-lg border border-slate-800 bg-slate-950">
        <div className="flex items-center justify-end gap-1 border-b border-slate-800 px-2 py-1">
          <button
            type="button"
            onClick={() => adjustZoom(-0.25)}
            aria-label="Zoom out"
            disabled={zoom <= MIN_ZOOM}
            className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-slate-200 disabled:opacity-40 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          >
            <Minus className="h-3.5 w-3.5" />
          </button>
          <span className="w-10 text-center text-xs tabular-nums text-slate-500">
            {Math.round(zoom * 100)}%
          </span>
          <button
            type="button"
            onClick={() => adjustZoom(0.25)}
            aria-label="Zoom in"
            disabled={zoom >= MAX_ZOOM}
            className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-slate-200 disabled:opacity-40 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          >
            <Plus className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={() => setZoom(1)}
            aria-label="Reset zoom"
            className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-slate-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          >
            <RotateCcw className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={() => setExpanded(true)}
            aria-label="Open diagram fullscreen"
            className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-slate-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          >
            <Maximize2 className="h-3.5 w-3.5" />
          </button>
        </div>
        <div className="overflow-auto p-4">{diagram}</div>
      </figure>

      {expanded && (
        <div className="fixed inset-0 z-[95] flex flex-col bg-slate-950/95 backdrop-blur">
          <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
            <span className="text-sm font-medium text-slate-300">Diagram</span>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => adjustZoom(-0.25)}
                aria-label="Zoom out"
                className="rounded p-1.5 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              >
                <Minus className="h-4 w-4" />
              </button>
              <span className="w-12 text-center text-xs tabular-nums text-slate-500">
                {Math.round(zoom * 100)}%
              </span>
              <button
                type="button"
                onClick={() => adjustZoom(0.25)}
                aria-label="Zoom in"
                className="rounded p-1.5 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              >
                <Plus className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={() => setExpanded(false)}
                aria-label="Close fullscreen diagram"
                className="ml-2 rounded p-1.5 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>
          <div className="flex-1 overflow-auto p-6">{diagram}</div>
        </div>
      )}
    </>
  );
}
