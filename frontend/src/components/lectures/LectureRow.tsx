"use client";

import {
  AlertCircle,
  CheckCircle2,
  Clock,
  FileText,
  Loader2,
  MoreHorizontal,
  RefreshCw,
  Sparkles,
  Trash2,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import type { IngestionStatus, Lecture } from "@/lib/types";
import { cn, relativeTime } from "@/lib/utils";

/**
 * One canonical status mapping, used everywhere a lecture appears.
 *
 * `processing` reports the stage rather than a bare spinner, and `failed`
 * carries the reason — it used to be a red badge with no explanation and no
 * way forward.
 */
export function StatusBadge({ lecture }: { lecture: Pick<Lecture, "ingestion_status" | "chunk_count"> }) {
  switch (lecture.ingestion_status) {
    case "ready":
      return (
        <Badge tone="success">
          <CheckCircle2 className="h-3 w-3" /> Ready · {lecture.chunk_count} sections
        </Badge>
      );
    case "processing":
      return (
        <Badge tone="info">
          <Loader2 className="h-3 w-3 animate-spin" /> Reading &amp; indexing
        </Badge>
      );
    case "failed":
      return (
        <Badge tone="danger">
          <XCircle className="h-3 w-3" /> Couldn&apos;t process
        </Badge>
      );
    default:
      return (
        <Badge tone="warning">
          <Clock className="h-3 w-3" /> Queued
        </Badge>
      );
  }
}

export const STATUS_LABEL: Record<IngestionStatus, string> = {
  pending: "Queued",
  processing: "Reading & indexing",
  ready: "Ready",
  failed: "Couldn't process",
};

export function LectureRow({
  lecture,
  onRetry,
  onDelete,
  retrying = false,
}: {
  lecture: Lecture;
  onRetry?: (lecture: Lecture) => void;
  onDelete?: (lecture: Lecture) => void;
  retrying?: boolean;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const isReady = lecture.ingestion_status === "ready";
  const isFailed = lecture.ingestion_status === "failed";

  return (
    <li className="rounded-xl border border-slate-800 bg-slate-900/50 transition-colors hover:border-slate-700">
      <div className="flex items-start gap-3 p-4">
        <div className="mt-0.5 shrink-0 rounded-lg bg-indigo-500/10 p-2 text-indigo-400">
          <FileText className="h-5 w-5" />
        </div>

        <div className="min-w-0 flex-1">
          <Link
            href={`/dashboard/lectures/${lecture.id}`}
            className="block truncate font-medium text-slate-100 hover:text-indigo-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 rounded"
          >
            {lecture.title || lecture.filename}
          </Link>
          <p className="mt-0.5 truncate text-xs text-slate-400">
            {relativeTime(lecture.uploaded_at)}
            {lecture.page_count > 0 && ` · ${lecture.page_count} pages`}
            {lecture.note_count > 0 &&
              ` · ${lecture.note_count} note${lecture.note_count === 1 ? "" : "s"}`}
          </p>

          <div className="mt-2 flex flex-wrap items-center gap-2">
            <StatusBadge lecture={lecture} />
          </div>

          {isFailed && lecture.error_message && (
            <div className="mt-3 flex items-start gap-2 rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span className="flex-1">{lecture.error_message}</span>
            </div>
          )}

          <div className="mt-3 flex flex-wrap gap-2">
            {isReady && (
              <>
                <Link href={`/dashboard/generate?lecture=${lecture.id}`}>
                  <Button size="sm" variant="secondary">
                    <Sparkles className="h-3.5 w-3.5" /> Generate notes
                  </Button>
                </Link>
                <Link href={`/dashboard/ask?lecture=${lecture.id}`}>
                  <Button size="sm" variant="ghost">
                    Ask about this
                  </Button>
                </Link>
              </>
            )}
            {isFailed && onRetry && (
              <Button size="sm" variant="secondary" onClick={() => onRetry(lecture)} isLoading={retrying}>
                <RefreshCw className="h-3.5 w-3.5" /> Retry
              </Button>
            )}
          </div>
        </div>

        {onDelete && (
          <div className="relative shrink-0">
            <button
              type="button"
              onClick={() => setMenuOpen((open) => !open)}
              aria-label={`More actions for ${lecture.title || lecture.filename}`}
              aria-expanded={menuOpen}
              className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-800 hover:text-slate-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
            >
              <MoreHorizontal className="h-4 w-4" />
            </button>
            {menuOpen && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} aria-hidden />
                <div className="absolute right-0 z-20 mt-1 w-44 overflow-hidden rounded-lg border border-slate-700 bg-slate-900 py-1 shadow-xl">
                  <button
                    type="button"
                    onClick={() => {
                      setMenuOpen(false);
                      onDelete(lecture);
                    }}
                    className={cn(
                      "flex w-full items-center gap-2 px-3 py-2 text-left text-sm",
                      "text-rose-400 hover:bg-slate-800",
                    )}
                  >
                    <Trash2 className="h-3.5 w-3.5" /> Delete lecture
                  </button>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </li>
  );
}
