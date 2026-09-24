"use client";

import { AlertTriangle, FileText, MessageSquare, Search, Sparkles, StickyNote } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorNotice } from "@/components/ui/ErrorState";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Skeleton } from "@/components/ui/Skeleton";
import { useCourses } from "@/hooks/useCourses";
import { useDebounced } from "@/hooks/useDebounced";
import { useSearch } from "@/hooks/useSearch";

/**
 * Semantic search across everything.
 *
 * The retrieval engine already did exactly this; it was simply never exposed
 * outside generation. Results group by source document, and each group offers
 * the two things you'd actually want next: generate from it, or ask about it.
 */
function SearchInner() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const [query, setQuery] = useState(searchParams.get("q") ?? "");
  const [scope, setScope] = useState<"all" | "lectures" | "notes">("all");
  const [courseId, setCourseId] = useState<string>("all");

  const debounced = useDebounced(query, 350);
  const { data: courses } = useCourses();
  const { data, isLoading, isFetching, isError, error, refetch } = useSearch({
    q: debounced,
    scope,
    courseId: courseId === "all" ? null : Number(courseId),
  });

  // Keep the URL shareable as the query settles.
  useEffect(() => {
    const next = debounced ? `/dashboard/search?q=${encodeURIComponent(debounced)}` : "/dashboard/search";
    window.history.replaceState(null, "", next);
  }, [debounced]);

  const hasQuery = debounced.trim().length > 1;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Search</h1>
        <p className="mt-1 text-sm text-slate-400">
          Searches meaning, not just words — across your lectures and your own notes.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-[1fr_auto_auto]">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <Input
            autoFocus
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="What are you looking for?"
            aria-label="Search query"
            className="pl-9"
          />
        </div>
        <Select
          value={scope}
          onChange={(event) => setScope(event.target.value as typeof scope)}
          aria-label="Search scope"
          className="sm:w-40"
        >
          <option value="all">Everything</option>
          <option value="lectures">Lectures only</option>
          <option value="notes">My notes only</option>
        </Select>
        <Select
          value={courseId}
          onChange={(event) => setCourseId(event.target.value)}
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
      </div>

      {isError && <ErrorNotice error={error} onRetry={() => refetch()} />}

      {!hasQuery ? (
        <EmptyState
          icon={<Search className="h-12 w-12" />}
          title="Search your material"
          description="Try a concept rather than an exact phrase — it matches on meaning."
          action={
            <div className="flex flex-wrap justify-center gap-2">
              {["gradient descent", "what is a hash table", "exam-relevant definitions"].map(
                (example) => (
                  <button
                    key={example}
                    type="button"
                    onClick={() => setQuery(example)}
                    className="rounded-full border border-slate-700 px-3 py-1.5 text-sm text-slate-300 hover:border-indigo-500/50 hover:text-slate-100"
                  >
                    {example}
                  </button>
                ),
              )}
            </div>
          }
        />
      ) : isLoading ? (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      ) : !data?.groups.length ? (
        <EmptyState
          icon={<Search className="h-12 w-12" />}
          title="Nothing matched"
          description={
            courseId !== "all" || scope !== "all"
              ? "Try widening the scope, or a different phrasing."
              : "Try a different phrasing, or upload the material you're looking for."
          }
          action={
            <Button
              variant="secondary"
              onClick={() => router.push(`/dashboard/ask?q=${encodeURIComponent(debounced)}`)}
            >
              <MessageSquare className="h-4 w-4" /> Ask it as a question instead
            </Button>
          }
        />
      ) : (
        <div className={isFetching ? "space-y-3 opacity-60" : "space-y-3"}>
          {data.degraded && (
            <div className="flex items-start gap-2 rounded-lg border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                Semantic search is unavailable right now, so these are plain text matches.
              </span>
            </div>
          )}

          <p className="text-sm text-slate-400">
            {data.groups.length} source{data.groups.length === 1 ? "" : "s"} · {data.total_hits}{" "}
            matching section{data.total_hits === 1 ? "" : "s"}
          </p>

          {data.groups.map((group) => (
            <Card key={`${group.kind}-${group.source_id}`}>
              <CardBody className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  {group.kind === "lecture" ? (
                    <FileText className="h-4 w-4 shrink-0 text-indigo-400" />
                  ) : (
                    <StickyNote className="h-4 w-4 shrink-0 text-emerald-400" />
                  )}
                  <Link
                    href={
                      group.kind === "lecture"
                        ? `/dashboard/lectures/${group.source_id}`
                        : `/dashboard/notes/${group.source_id}`
                    }
                    className="min-w-0 flex-1 truncate font-medium text-slate-100 hover:text-indigo-300"
                  >
                    {group.title}
                  </Link>
                  {group.course_name && <Badge tone="neutral">{group.course_name}</Badge>}
                  {group.best_score !== null && group.best_score !== undefined && (
                    <span className="text-xs text-slate-500">
                      {Math.round(group.best_score * 100)}% match
                    </span>
                  )}
                </div>

                <ul className="space-y-2">
                  {group.excerpts.slice(0, 3).map((excerpt, index) => (
                    <li
                      key={index}
                      className="rounded-lg border border-slate-800 bg-slate-950/50 p-3 text-sm text-slate-400"
                    >
                      {excerpt.page ? (
                        <span className="mr-2 text-xs text-slate-500">p.{excerpt.page}</span>
                      ) : null}
                      {excerpt.text}
                    </li>
                  ))}
                </ul>

                <div className="flex flex-wrap gap-2">
                  {group.kind === "lecture" && (
                    <Link href={`/dashboard/generate?lecture=${group.source_id}`}>
                      <Button size="sm" variant="secondary">
                        <Sparkles className="h-3.5 w-3.5" /> Generate notes on this
                      </Button>
                    </Link>
                  )}
                  <Link
                    href={
                      group.kind === "lecture"
                        ? `/dashboard/ask?lecture=${group.source_id}&q=${encodeURIComponent(debounced)}`
                        : `/dashboard/notes/${group.source_id}`
                    }
                  >
                    <Button size="sm" variant="ghost">
                      <MessageSquare className="h-3.5 w-3.5" />
                      {group.kind === "lecture" ? "Ask about this" : "Open note"}
                    </Button>
                  </Link>
                </div>
              </CardBody>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<Skeleton className="h-64 w-full" />}>
      <SearchInner />
    </Suspense>
  );
}
