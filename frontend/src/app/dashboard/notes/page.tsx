"use client";

import { Search, Sparkles, StickyNote } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { NoteCard } from "@/components/notes/NoteCard";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorPage } from "@/components/ui/ErrorState";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Skeleton } from "@/components/ui/Skeleton";
import { useCourses } from "@/hooks/useCourses";
import { useDebounced } from "@/hooks/useDebounced";
import { useNotes } from "@/hooks/useNotes";
import { NOTE_TYPE_LABELS } from "@/lib/utils";

const PAGE_SIZE = 24;

/**
 * Every note, browsable.
 *
 * There was no list endpoint at all: notes existed only as the five most recent
 * entries on the dashboard, so anything older was unreachable.
 */
export default function NotesPage() {
  const [query, setQuery] = useState("");
  const [courseId, setCourseId] = useState<string>("all");
  const [noteType, setNoteType] = useState<string>("all");
  const [rootsOnly, setRootsOnly] = useState(true);
  const [page, setPage] = useState(0);

  const debouncedQuery = useDebounced(query, 300);
  const { data: courses } = useCourses();

  const { data, isLoading, isError, error, refetch, isFetching } = useNotes({
    q: debouncedQuery,
    courseId: courseId === "all" ? null : Number(courseId),
    noteType: noteType === "all" ? null : noteType,
    rootsOnly,
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  });

  if (isError) return <ErrorPage error={error} onRetry={() => refetch()} />;

  const total = data?.total ?? 0;
  const pageCount = Math.ceil(total / PAGE_SIZE);
  const filtered = debouncedQuery || courseId !== "all" || noteType !== "all";

  const resetPage = <T,>(setter: (value: T) => void) => (value: T) => {
    setPage(0);
    setter(value);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Notes</h1>
          <p className="mt-1 text-sm text-slate-400">
            {total} note{total === 1 ? "" : "s"}
            {rootsOnly && " · revisions hidden"}
          </p>
        </div>
        <Link href="/dashboard/generate">
          <Button>
            <Sparkles className="h-4 w-4" /> Generate notes
          </Button>
        </Link>
      </div>

      <div className="grid gap-3 sm:grid-cols-[1fr_auto_auto]">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <Input
            value={query}
            onChange={(event) => resetPage(setQuery)(event.target.value)}
            placeholder="Search your notes…"
            aria-label="Search notes"
            className="pl-9"
          />
        </div>
        <Select
          value={courseId}
          onChange={(event) => resetPage(setCourseId)(event.target.value)}
          aria-label="Filter by course"
          className="sm:w-48"
        >
          <option value="all">All courses</option>
          {(courses ?? []).map((course) => (
            <option key={course.id} value={course.id}>
              {course.name}
            </option>
          ))}
        </Select>
        <Select
          value={noteType}
          onChange={(event) => resetPage(setNoteType)(event.target.value)}
          aria-label="Filter by type"
          className="sm:w-48"
        >
          <option value="all">All types</option>
          {Object.entries(NOTE_TYPE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
      </div>

      <label className="flex w-fit items-center gap-2 text-sm text-slate-400">
        <input
          type="checkbox"
          checked={rootsOnly}
          onChange={(event) => resetPage(setRootsOnly)(event.target.checked)}
          className="h-4 w-4 rounded border-slate-600 accent-indigo-500"
        />
        Hide revisions
      </label>

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-36 w-full" />
          ))}
        </div>
      ) : !data?.items.length ? (
        <EmptyState
          icon={<StickyNote className="h-12 w-12" />}
          title={filtered ? "No notes match those filters" : "No notes yet"}
          description={
            filtered
              ? "Try a different search, or clear the filters."
              : "Generate notes from a lecture and they'll collect here."
          }
          action={
            filtered ? (
              <Button
                variant="secondary"
                onClick={() => {
                  setQuery("");
                  setCourseId("all");
                  setNoteType("all");
                  setPage(0);
                }}
              >
                Clear filters
              </Button>
            ) : (
              <Link href="/dashboard/generate">
                <Button>
                  <Sparkles className="h-4 w-4" /> Generate notes
                </Button>
              </Link>
            )
          }
        />
      ) : (
        <>
          <ul
            className={`grid gap-3 sm:grid-cols-2 lg:grid-cols-3 ${isFetching ? "opacity-60" : ""}`}
          >
            {data.items.map((note) => (
              <NoteCard key={note.id} note={note} />
            ))}
          </ul>

          {pageCount > 1 && (
            <div className="flex items-center justify-between gap-3 pt-2">
              <Button
                variant="secondary"
                size="sm"
                disabled={page === 0}
                onClick={() => setPage((p) => Math.max(0, p - 1))}
              >
                Previous
              </Button>
              <span className="text-sm text-slate-400">
                Page {page + 1} of {pageCount}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={page + 1 >= pageCount}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
