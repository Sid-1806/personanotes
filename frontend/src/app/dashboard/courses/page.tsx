"use client";

import { BookOpen, FileText, Plus, StickyNote } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorPage } from "@/components/ui/ErrorState";
import { Field, Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Skeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { useCourses, useCreateCourse } from "@/hooks/useCourses";
import { errorMessage } from "@/lib/api";
import { COURSE_COLORS, cn, courseColor, relativeTime } from "@/lib/utils";

/** Courses: the organising layer a flat lecture list never had. */
export default function CoursesPage() {
  const { data: courses, isLoading, isError, error, refetch } = useCourses();
  const createCourse = useCreateCourse();
  const toast = useToast();

  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [color, setColor] = useState<string>("indigo");

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!name.trim()) return;
    try {
      await createCourse.mutateAsync({ name: name.trim(), code: code.trim() || undefined, color });
      toast.success(`Created ${name.trim()}.`);
      setOpen(false);
      setName("");
      setCode("");
      setColor("indigo");
    } catch (createError) {
      toast.error(errorMessage(createError, "Couldn't create that course."));
    }
  };

  if (isError) return <ErrorPage error={error} onRetry={() => refetch()} />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Courses</h1>
          <p className="mt-1 text-sm text-slate-400">
            Each course keeps its lectures and notes together, and scopes search and questions.
          </p>
        </div>
        <Button onClick={() => setOpen(true)}>
          <Plus className="h-4 w-4" /> New course
        </Button>
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-36 w-full" />
          ))}
        </div>
      ) : !courses?.length ? (
        <EmptyState
          icon={<BookOpen className="h-12 w-12" />}
          title="No courses yet"
          description="Courses keep each subject's lectures and notes together — and let you search or ask questions across a whole term."
          action={
            <Button onClick={() => setOpen(true)}>
              <Plus className="h-4 w-4" /> Create your first course
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {courses.map((course) => {
            const accent = courseColor(course.color);
            return (
              <Link key={course.id} href={`/dashboard/courses/${course.id}`} className="group">
                <Card className={cn("h-full transition-colors", accent.ring)}>
                  <CardBody className="flex h-full flex-col">
                    <div className="flex items-start gap-2">
                      <span className={cn("mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full", accent.dot)} />
                      <div className="min-w-0 flex-1">
                        <h2 className="truncate font-semibold text-slate-100">{course.name}</h2>
                        {course.code && (
                          <p className="truncate text-xs text-slate-400">{course.code}</p>
                        )}
                      </div>
                    </div>

                    <div className="mt-4 flex flex-wrap gap-4 text-sm text-slate-400">
                      <span className="inline-flex items-center gap-1.5">
                        <FileText className="h-3.5 w-3.5" /> {course.lecture_count} lecture
                        {course.lecture_count === 1 ? "" : "s"}
                      </span>
                      <span className="inline-flex items-center gap-1.5">
                        <StickyNote className="h-3.5 w-3.5" /> {course.note_count} note
                        {course.note_count === 1 ? "" : "s"}
                      </span>
                    </div>

                    <div className="mt-3 flex flex-wrap gap-2 text-xs">
                      {course.processing_lecture_count > 0 && (
                        <span className="rounded-full border border-indigo-500/25 bg-indigo-500/10 px-2 py-0.5 text-indigo-300">
                          {course.processing_lecture_count} processing
                        </span>
                      )}
                      {course.failed_lecture_count > 0 && (
                        <span className="rounded-full border border-rose-500/25 bg-rose-500/10 px-2 py-0.5 text-rose-300">
                          {course.failed_lecture_count} needs attention
                        </span>
                      )}
                    </div>

                    <p className="mt-auto pt-4 text-xs text-slate-500">
                      {course.last_activity_at
                        ? `Active ${relativeTime(course.last_activity_at)}`
                        : "Nothing here yet"}
                    </p>
                  </CardBody>
                </Card>
              </Link>
            );
          })}
        </div>
      )}

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="New course"
        description="You can rename or recolour it later."
        footer={
          <>
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button onClick={submit} isLoading={createCourse.isPending} disabled={!name.trim()}>
              Create course
            </Button>
          </>
        }
      >
        <form onSubmit={submit} className="space-y-4">
          <Field label="Name" htmlFor="new-course-name">
            <Input
              id="new-course-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="e.g. Machine Learning"
            />
          </Field>
          <Field label="Code" htmlFor="new-course-code" hint="Optional — e.g. CS229.">
            <Input
              id="new-course-code"
              value={code}
              onChange={(event) => setCode(event.target.value)}
            />
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
        </form>
      </Modal>
    </div>
  );
}
