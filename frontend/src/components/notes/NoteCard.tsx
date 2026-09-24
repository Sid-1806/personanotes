import { FileText, GitBranch, Pencil } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import type { NoteSummary } from "@/lib/types";
import { noteTypeLabel, readingTime, relativeTime } from "@/lib/utils";

/** One note in a list. Says enough to pick the right one without opening it. */
export function NoteCard({ note }: { note: NoteSummary }) {
  return (
    <li>
      <Link
        href={`/dashboard/notes/${note.id}`}
        className="group flex h-full flex-col rounded-xl border border-slate-800 bg-slate-900/50 p-4 transition-colors hover:border-indigo-500/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
      >
        <div className="flex items-start gap-2">
          <h3 className="min-w-0 flex-1 truncate font-medium text-slate-100 group-hover:text-indigo-300">
            {note.title ?? `Notes ${note.id}`}
          </h3>
          {note.has_edits && (
            <Badge tone="info">
              <Pencil className="h-3 w-3" /> Edited
            </Badge>
          )}
        </div>

        {note.excerpt && (
          <p className="mt-1.5 line-clamp-2 text-sm text-slate-400">{note.excerpt}</p>
        )}

        <div className="mt-auto flex flex-wrap items-center gap-x-3 gap-y-1 pt-3 text-xs text-slate-500">
          <span>{noteTypeLabel(note.note_type)}</span>
          <span>{readingTime(note.word_count)}</span>
          {note.lecture_title && (
            <span className="inline-flex min-w-0 items-center gap-1">
              <FileText className="h-3 w-3 shrink-0" />
              <span className="truncate">{note.lecture_title}</span>
            </span>
          )}
          {note.parent_note_id && (
            <span className="inline-flex items-center gap-1" title="A revision of an earlier note">
              <GitBranch className="h-3 w-3" /> Revision
            </span>
          )}
          <span className="ml-auto">{relativeTime(note.created_at)}</span>
        </div>
      </Link>
    </li>
  );
}
