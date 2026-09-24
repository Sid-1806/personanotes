"use client";

import {
  AlertCircle,
  ArrowLeft,
  Eye,
  FileText,
  Loader2,
  RefreshCw,
  Sparkles,
  StickyNote,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { ChatPanel } from "@/components/chat/ChatPanel";
import { StatusBadge } from "@/components/lectures/LectureRow";
import { NoteCard } from "@/components/notes/NoteCard";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorPage } from "@/components/ui/ErrorState";
import { Field, Input } from "@/components/ui/Input";
import { Skeleton } from "@/components/ui/Skeleton";
import { Tabs } from "@/components/ui/Tabs";
import { useToast } from "@/components/ui/Toast";
import { useLecture, useLectureNotes, useLectureText, useLectures } from "@/hooks/useLectures";
import { errorMessage } from "@/lib/api";
import { formatDate } from "@/lib/utils";

/**
 * Lecture detail.
 *
 * `GET /lectures/{id}` existed with no page behind it. This is where you check
 * what was actually extracted from a file, recover from a failure, and find
 * everything generated from it.
 */
export default function LecturePage() {
  const params = useParams();
  const lectureId = Number(params?.id);
  const toast = useToast();

  const { data: lecture, isLoading, isError, error, refetch } = useLecture(lectureId);
  const { data: notes } = useLectureNotes(lectureId);
  const { retry, update } = useLectures();

  const [tab, setTab] = useState("notes");
  const [showText, setShowText] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [title, setTitle] = useState("");

  const { data: extracted, isLoading: textLoading } = useLectureText(lectureId, showText);

  if (isError) return <ErrorPage error={error} onRetry={() => refetch()} />;
  if (isLoading || !lecture) return <Skeleton className="h-64 w-full" />;

  const saveTitle = async () => {
    try {
      await update.mutateAsync({ id: lectureId, title: title.trim() });
      toast.success("Lecture renamed.");
      setRenaming(false);
    } catch (renameError) {
      toast.error(errorMessage(renameError, "Couldn't rename that."));
    }
  };

  const isReady = lecture.ingestion_status === "ready";

  return (
    <div className="space-y-6">
      <Link
        href={lecture.course_id ? `/dashboard/courses/${lecture.course_id}` : "/dashboard/courses"}
        className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-200"
      >
        <ArrowLeft className="h-4 w-4" /> {lecture.course_name ?? "Courses"}
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <span className="mt-1 shrink-0 rounded-lg bg-indigo-500/10 p-2.5 text-indigo-400">
            <FileText className="h-5 w-5" />
          </span>
          <div className="min-w-0">
            {renaming ? (
              <div className="flex flex-wrap items-end gap-2">
                <Field label="Title" htmlFor="lecture-title">
                  <Input
                    id="lecture-title"
                    value={title}
                    onChange={(event) => setTitle(event.target.value)}
                    className="w-64"
                  />
                </Field>
                <Button size="sm" onClick={saveTitle} isLoading={update.isPending}>
                  Save
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setRenaming(false)}>
                  Cancel
                </Button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => {
                  setTitle(lecture.title ?? lecture.filename);
                  setRenaming(true);
                }}
                className="max-w-full truncate text-left text-2xl font-bold text-slate-100 hover:text-indigo-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 rounded"
                title="Click to rename"
              >
                {lecture.title || lecture.filename}
              </button>
            )}
            <p className="mt-1 text-sm text-slate-400">
              {[
                formatDate(lecture.uploaded_at),
                lecture.page_count > 0 && `${lecture.page_count} pages`,
                lecture.chunk_count > 0 && `${lecture.chunk_count} indexed sections`,
              ]
                .filter(Boolean)
                .join(" · ")}
            </p>
            <div className="mt-2">
              <StatusBadge lecture={lecture} />
            </div>
          </div>
        </div>

        {isReady && (
          <Link href={`/dashboard/generate?lecture=${lecture.id}`}>
            <Button size="sm">
              <Sparkles className="h-4 w-4" /> Generate notes
            </Button>
          </Link>
        )}
      </div>

      {lecture.ingestion_status === "failed" && (
        <Card className="border-rose-500/30">
          <CardBody className="flex flex-wrap items-start gap-3">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-rose-400" />
            <div className="min-w-0 flex-1">
              <p className="font-medium text-rose-200">This lecture couldn&apos;t be processed</p>
              <p className="mt-1 text-sm text-rose-300/90">
                {lecture.error_message ?? "Processing failed."}
              </p>
            </div>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => retry.mutate(lecture.id)}
              isLoading={retry.isPending}
            >
              <RefreshCw className="h-4 w-4" /> Retry
            </Button>
          </CardBody>
        </Card>
      )}

      {(lecture.ingestion_status === "processing" || lecture.ingestion_status === "pending") && (
        <Card>
          <CardBody className="flex items-center gap-3 text-sm text-slate-300">
            <Loader2 className="h-4 w-4 animate-spin text-indigo-400" />
            {lecture.ingestion_status === "pending"
              ? "Queued for processing…"
              : "Reading the file, splitting it into sections and indexing them…"}
          </CardBody>
        </Card>
      )}

      <Tabs
        items={[
          { id: "notes", label: "Notes", count: notes?.length ?? 0 },
          { id: "ask", label: "Ask" },
          { id: "source", label: "Source text" },
        ]}
        active={tab}
        onChange={setTab}
      />

      {tab === "notes" &&
        (!notes?.length ? (
          <EmptyState
            icon={<StickyNote className="h-12 w-12" />}
            title="Nothing generated from this lecture yet"
            description={
              isReady
                ? "Turn it into full notes, a summary, a cheat sheet or practice questions."
                : "Once processing finishes you'll be able to generate notes from it."
            }
            action={
              isReady ? (
                <Link href={`/dashboard/generate?lecture=${lecture.id}`}>
                  <Button>
                    <Sparkles className="h-4 w-4" /> Generate notes
                  </Button>
                </Link>
              ) : undefined
            }
          />
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2">
            {notes.map((note) => (
              <NoteCard key={note.id} note={note} />
            ))}
          </ul>
        ))}

      {tab === "ask" && (
        <Card>
          <CardBody>
            <ChatPanel
              scope={{ scope: "lecture", lecture_id: lectureId, course_id: lecture.course_id }}
              className="h-[60vh]"
              placeholder="Ask about this lecture…"
            />
          </CardBody>
        </Card>
      )}

      {tab === "source" && (
        <Card>
          <CardHeader className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-slate-200">What was extracted</h2>
            {!showText && (
              <Button size="sm" variant="secondary" onClick={() => setShowText(true)}>
                <Eye className="h-4 w-4" /> Show text
              </Button>
            )}
          </CardHeader>
          <CardBody>
            {!showText ? (
              <p className="text-sm text-slate-400">
                Check exactly what the parser read from this file — useful when notes come out
                thinner than expected.
              </p>
            ) : textLoading ? (
              <Skeleton className="h-64 w-full" />
            ) : !extracted?.text.trim() ? (
              <p className="text-sm text-slate-400">No text could be extracted from this file.</p>
            ) : (
              <>
                <pre className="max-h-[50vh] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-950 p-4 text-xs leading-relaxed text-slate-300">
                  {extracted.text}
                </pre>
                {extracted.truncated && (
                  <p className="mt-2 text-xs text-slate-500">
                    Showing the first 20,000 characters.
                  </p>
                )}
              </>
            )}
          </CardBody>
        </Card>
      )}
    </div>
  );
}
