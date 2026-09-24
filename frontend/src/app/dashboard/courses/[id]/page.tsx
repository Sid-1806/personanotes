"use client";

import { ArrowLeft, FileText, Settings2, Sparkles, StickyNote, Trash2 } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { ChatPanel } from "@/components/chat/ChatPanel";
import { LectureRow } from "@/components/lectures/LectureRow";
import { UploadDropzone } from "@/components/lectures/UploadDropzone";
import { NoteCard } from "@/components/notes/NoteCard";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorPage } from "@/components/ui/ErrorState";
import { Field, Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Skeleton } from "@/components/ui/Skeleton";
import { Tabs } from "@/components/ui/Tabs";
import { useToast } from "@/components/ui/Toast";
import { useCourse, useDeleteCourse, useUpdateCourse } from "@/hooks/useCourses";
import { useLectures } from "@/hooks/useLectures";
import { useNotes } from "@/hooks/useNotes";
import { errorMessage } from "@/lib/api";
import type { Lecture } from "@/lib/types";
import { COURSE_COLORS, cn, courseColor } from "@/lib/utils";

/** The course workspace — where a student actually lives during a term. */
function CourseWorkspace() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const toast = useToast();

  const courseId = Number(params?.id);
  const [tab, setTab] = useState(searchParams.get("tab") ?? "lectures");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<Lecture | null>(null);

  const { data: course, isLoading, isError, error, refetch } = useCourse(courseId);
  const { lectures, isLoading: lecturesLoading, upload, retry, remove } = useLectures({ courseId });
  const { data: notes } = useNotes({ courseId, limit: 50 });

  const updateCourse = useUpdateCourse();
  const deleteCourse = useDeleteCourse();

  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [color, setColor] = useState("indigo");

  const openSettings = () => {
    setName(course?.name ?? "");
    setCode(course?.code ?? "");
    setColor(course?.color ?? "indigo");
    setSettingsOpen(true);
  };

  const saveSettings = async () => {
    try {
      await updateCourse.mutateAsync({ id: courseId, name: name.trim(), code: code.trim(), color });
      toast.success("Course updated.");
      setSettingsOpen(false);
    } catch (updateError) {
      toast.error(errorMessage(updateError, "Couldn't save those changes."));
    }
  };

  const removeCourse = async () => {
    try {
      await deleteCourse.mutateAsync(courseId);
      toast.success("Course deleted. Its lectures and notes were kept.");
      router.push("/dashboard/courses");
    } catch (deleteError) {
      toast.error(errorMessage(deleteError, "Couldn't delete that course."));
    }
  };

  const handleUpload = async (files: File[]) => {
    try {
      await upload.mutateAsync({ files, courseId });
      toast.success(`Uploading ${files.length} file${files.length === 1 ? "" : "s"}.`);
    } catch (uploadError) {
      toast.error(errorMessage(uploadError, "That upload didn't go through."));
    }
  };

  const deleteLecture = async (keepNotes: boolean) => {
    if (!confirmDelete) return;
    const target = confirmDelete;
    setConfirmDelete(null);
    try {
      await remove.mutateAsync({ id: target.id, keepNotes });
      toast.success(`Deleted ${target.title || target.filename}.`);
    } catch (deleteError) {
      toast.error(errorMessage(deleteError, "Couldn't delete that lecture."));
    }
  };

  if (isError) return <ErrorPage error={error} onRetry={() => refetch()} />;
  if (isLoading || !course) return <Skeleton className="h-64 w-full" />;

  const accent = courseColor(course.color);

  return (
    <div className="space-y-6">
      <Link
        href="/dashboard/courses"
        className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-200"
      >
        <ArrowLeft className="h-4 w-4" /> All courses
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <span className={cn("mt-2 h-3 w-3 shrink-0 rounded-full", accent.dot)} />
          <div className="min-w-0">
            <h1 className="truncate text-2xl font-bold text-slate-100">{course.name}</h1>
            <p className="mt-1 text-sm text-slate-400">
              {course.code ? `${course.code} · ` : ""}
              {course.lecture_count} lecture{course.lecture_count === 1 ? "" : "s"} ·{" "}
              {course.note_count} note{course.note_count === 1 ? "" : "s"}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Link href={`/dashboard/generate?course=${courseId}`}>
            <Button size="sm">
              <Sparkles className="h-4 w-4" /> Generate
            </Button>
          </Link>
          <Button size="sm" variant="ghost" onClick={openSettings} aria-label="Course settings">
            <Settings2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <Tabs
        items={[
          { id: "lectures", label: "Lectures", count: lectures.length },
          { id: "notes", label: "Notes", count: notes?.total ?? 0 },
          { id: "ask", label: "Ask" },
        ]}
        active={tab}
        onChange={setTab}
      />

      {tab === "lectures" && (
        <div className="space-y-4">
          <UploadDropzone
            onFiles={handleUpload}
            uploading={upload.isPending}
            error={upload.isError ? upload.error : undefined}
            compact={lectures.length > 0}
          />

          {lecturesLoading ? (
            <div className="space-y-3">
              {[0, 1].map((i) => (
                <Skeleton key={i} className="h-24 w-full" />
              ))}
            </div>
          ) : lectures.length === 0 ? (
            <p className="py-6 text-center text-sm text-slate-400">
              No lectures in this course yet — add the first one above.
            </p>
          ) : (
            <ul className="space-y-3">
              {lectures.map((lecture) => (
                <LectureRow
                  key={lecture.id}
                  lecture={lecture}
                  onRetry={(target) => retry.mutate(target.id)}
                  onDelete={setConfirmDelete}
                  retrying={retry.isPending && retry.variables === lecture.id}
                />
              ))}
            </ul>
          )}
        </div>
      )}

      {tab === "notes" && (
        <div>
          {!notes?.items.length ? (
            <EmptyState
              icon={<StickyNote className="h-12 w-12" />}
              title="No notes in this course yet"
              description="Generate notes from one of its lectures and they'll collect here."
              action={
                <Link href={`/dashboard/generate?course=${courseId}`}>
                  <Button>
                    <Sparkles className="h-4 w-4" /> Generate notes
                  </Button>
                </Link>
              }
            />
          ) : (
            <ul className="grid gap-3 sm:grid-cols-2">
              {notes.items.map((note) => (
                <NoteCard key={note.id} note={note} />
              ))}
            </ul>
          )}
        </div>
      )}

      {tab === "ask" && (
        <Card>
          <CardBody>
            <ChatPanel
              scope={{ scope: "course", course_id: courseId }}
              className="h-[60vh]"
              placeholder={`Ask about ${course.name}…`}
            />
          </CardBody>
        </Card>
      )}

      <Modal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        title="Course settings"
        footer={
          <>
            <Button
              variant="danger"
              onClick={removeCourse}
              isLoading={deleteCourse.isPending}
              className="mr-auto"
            >
              <Trash2 className="h-4 w-4" /> Delete course
            </Button>
            <Button variant="ghost" onClick={() => setSettingsOpen(false)}>
              Cancel
            </Button>
            <Button onClick={saveSettings} isLoading={updateCourse.isPending}>
              Save
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field label="Name" htmlFor="course-name">
            <Input id="course-name" value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
          <Field label="Code" htmlFor="course-code">
            <Input id="course-code" value={code} onChange={(e) => setCode(e.target.value)} />
          </Field>
          <fieldset>
            <legend className="mb-1.5 text-sm font-medium text-slate-300">Colour</legend>
            <div className="flex flex-wrap gap-2">
              {COURSE_COLORS.map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => setColor(option)}
                  aria-label={option}
                  aria-pressed={color === option}
                  className={cn(
                    "h-7 w-7 rounded-full border-2 transition-transform",
                    courseColor(option).dot,
                    color === option ? "border-slate-100 scale-110" : "border-transparent",
                  )}
                />
              ))}
            </div>
          </fieldset>
          <p className="text-xs text-slate-400">
            Deleting a course keeps its lectures and notes — they move to Uncategorized.
          </p>
        </div>
      </Modal>

      <Modal
        open={confirmDelete !== null}
        onClose={() => setConfirmDelete(null)}
        title={`Delete ${confirmDelete?.title || confirmDelete?.filename || "this lecture"}?`}
        description="This removes the file and its search index. It can't be undone."
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirmDelete(null)}>
              Cancel
            </Button>
            {(confirmDelete?.note_count ?? 0) > 0 && (
              <Button variant="danger" onClick={() => deleteLecture(false)}>
                Delete notes too
              </Button>
            )}
            <Button variant="danger" onClick={() => deleteLecture(true)}>
              {(confirmDelete?.note_count ?? 0) > 0 ? "Keep notes" : "Delete"}
            </Button>
          </>
        }
      >
        {(confirmDelete?.note_count ?? 0) > 0 && (
          <p className="text-sm text-slate-300">
            {confirmDelete?.note_count} note
            {confirmDelete?.note_count === 1 ? "" : "s"} were generated from this lecture. Keeping
            them leaves them intact but without a source link.
          </p>
        )}
      </Modal>
    </div>
  );
}

export default function CoursePage() {
  return (
    <Suspense fallback={<Skeleton className="h-64 w-full" />}>
      <CourseWorkspace />
    </Suspense>
  );
}
