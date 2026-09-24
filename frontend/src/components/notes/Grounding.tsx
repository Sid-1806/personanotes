"use client";

import { AlertTriangle, ChevronDown, FileText, Layers, Sparkles } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Badge } from "@/components/ui/Badge";
import type { Grounding } from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * Grounding chips that expand into the actual retrieved text.
 *
 * The excerpts were always fetched during retrieval and then thrown away, so
 * the UI could only ever say "grounded in 5 sections". Persisting them means a
 * claim in a note can be checked against the source that produced it.
 */
export function GroundingPanel({
  grounding,
  className,
}: {
  grounding: Grounding;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const count = grounding?.chunks_used ?? 0;
  const excerpts = grounding?.excerpts ?? [];

  if (count === 0) {
    return (
      <div
        className={cn(
          "flex items-start gap-2 rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-sm text-amber-300",
          className,
        )}
      >
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
        <span>
          No matching lecture sections were found, so this note leans on general knowledge.
          Upload the relevant lecture for grounded notes.
        </span>
      </div>
    );
  }

  return (
    <div className={className}>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/50 px-3 py-2 text-left text-sm text-slate-300 transition-colors hover:border-slate-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50"
      >
        <Layers className="h-4 w-4 shrink-0 text-emerald-400" />
        <span className="flex-1">
          Grounded in {count} section{count === 1 ? "" : "s"}
          {excerpts.length > 0 && (
            <span className="ml-1 text-slate-500">— tap to see the source text</span>
          )}
        </span>
        <ChevronDown
          className={cn("h-4 w-4 shrink-0 text-slate-500 transition-transform", open && "rotate-180")}
        />
      </button>

      {open && excerpts.length > 0 && (
        <ul className="mt-2 space-y-2">
          {excerpts.map((excerpt, index) => (
            <li
              key={index}
              className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 text-sm"
            >
              <div className="mb-1.5 flex flex-wrap items-center gap-2 text-xs text-slate-400">
                <span className="inline-flex h-5 w-5 items-center justify-center rounded bg-slate-800 font-mono text-[11px] text-slate-300">
                  {index + 1}
                </span>
                {excerpt.note_id ? (
                  <Link
                    href={`/dashboard/notes/${excerpt.note_id}`}
                    className="inline-flex items-center gap-1 text-emerald-400 hover:underline"
                  >
                    <Sparkles className="h-3 w-3" />
                    {excerpt.note_title ?? "Your notes"}
                  </Link>
                ) : excerpt.lecture_id ? (
                  <Link
                    href={`/dashboard/lectures/${excerpt.lecture_id}`}
                    className="inline-flex items-center gap-1 text-indigo-400 hover:underline"
                  >
                    <FileText className="h-3 w-3" />
                    {excerpt.lecture_title ?? `Lecture ${excerpt.lecture_id}`}
                  </Link>
                ) : (
                  <span className="inline-flex items-center gap-1">
                    <Sparkles className="h-3 w-3" /> Your material
                  </span>
                )}
                {excerpt.page ? <span>p.{excerpt.page}</span> : null}
                {excerpt.score !== null && excerpt.score !== undefined && (
                  <span className="text-slate-500">{Math.round(excerpt.score * 100)}% match</span>
                )}
              </div>
              <p className="whitespace-pre-wrap text-slate-400">{excerpt.text}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Compact grounding chip for list rows and headers. */
export function GroundingBadge({ grounding }: { grounding: Grounding }) {
  const count = grounding?.chunks_used ?? 0;
  return (
    <Badge tone={count > 0 ? "success" : "warning"}>
      <Layers className="h-3 w-3" />
      {count > 0 ? `${count} source${count === 1 ? "" : "s"}` : "Not grounded"}
    </Badge>
  );
}
