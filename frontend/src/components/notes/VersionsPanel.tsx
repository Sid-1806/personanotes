"use client";

import { GitBranch, Pencil, Sparkles } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Markdown } from "@/components/notes/Markdown";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Skeleton } from "@/components/ui/Skeleton";
import { useNoteDiff, useNoteVersions } from "@/hooks/useNotes";
import type { NoteVersion } from "@/lib/types";
import { cn, relativeTime } from "@/lib/utils";

/**
 * A note's history: generations, refinements and the user's own edits.
 *
 * Refinements used to be unrelated rows, so "how did this change over time?"
 * was unanswerable. `parent_note_id` turns the chain into a timeline, and the
 * diff engine that already powers style learning does the comparison.
 */
export function VersionsPanel({ noteId }: { noteId: number }) {
  const { data, isLoading } = useNoteVersions(noteId);
  const [compareWith, setCompareWith] = useState<number | null>(null);

  if (isLoading) return <Skeleton className="h-40 w-full" />;
  if (!data?.versions.length) return null;

  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-400">
        Every generation, revision and edit of this note, oldest first.
      </p>

      <ol className="space-y-2">
        {data.versions.map((version) => (
          <VersionRow
            key={`${version.kind}-${version.id}`}
            version={version}
            currentNoteId={noteId}
            onCompare={() => setCompareWith(version.note_id)}
          />
        ))}
      </ol>

      <DiffModal
        noteId={noteId}
        against={compareWith}
        onClose={() => setCompareWith(null)}
      />
    </div>
  );
}

function VersionRow({
  version,
  currentNoteId,
  onCompare,
}: {
  version: NoteVersion;
  currentNoteId: number;
  onCompare: () => void;
}) {
  const Icon = version.kind === "edited" ? Pencil : version.kind === "refined" ? GitBranch : Sparkles;
  const isCurrent = version.note_id === currentNoteId;

  return (
    <li
      className={cn(
        "flex flex-wrap items-center gap-3 rounded-lg border px-3 py-2.5 text-sm",
        isCurrent ? "border-indigo-500/40 bg-indigo-500/5" : "border-slate-800 bg-slate-900/40",
      )}
    >
      <Icon className="h-4 w-4 shrink-0 text-slate-500" />
      <div className="min-w-0 flex-1">
        <p className="truncate text-slate-200">
          {version.label}
          {version.is_current && <Badge tone="info" className="ml-2">Current</Badge>}
        </p>
        <p className="text-xs text-slate-500">
          {relativeTime(version.created_at)} · {version.word_count.toLocaleString()} words
        </p>
      </div>

      {!isCurrent && (
        <div className="flex gap-1">
          <Button size="sm" variant="ghost" onClick={onCompare}>
            Compare
          </Button>
          <Link href={`/dashboard/notes/${version.note_id}`}>
            <Button size="sm" variant="ghost">
              Open
            </Button>
          </Link>
        </div>
      )}
    </li>
  );
}

function DiffModal({
  noteId,
  against,
  onClose,
}: {
  noteId: number;
  against: number | null;
  onClose: () => void;
}) {
  const { data, isLoading } = useNoteDiff(noteId, against);
  const similarity = data?.stats?.personalization_score;

  return (
    <Modal
      open={against !== null}
      onClose={onClose}
      size="xl"
      title="Compare versions"
      description={
        similarity !== undefined
          ? `These two are ${Math.round(similarity)}% alike in style.`
          : undefined
      }
    >
      {isLoading || !data ? (
        <Skeleton className="h-64 w-full" />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              {data.from_label}
            </h3>
            <div className="max-h-[55vh] overflow-y-auto rounded-lg border border-slate-800 bg-slate-950/50 p-4">
              <Markdown compact>{data.from_markdown}</Markdown>
            </div>
          </section>
          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-indigo-400">
              {data.to_label}
            </h3>
            <div className="max-h-[55vh] overflow-y-auto rounded-lg border border-indigo-500/25 bg-slate-950/50 p-4">
              <Markdown compact>{data.to_markdown}</Markdown>
            </div>
          </section>
        </div>
      )}
    </Modal>
  );
}
