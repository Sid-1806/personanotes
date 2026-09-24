"use client";

import { ArrowRight, BookOpen, Check, FileText, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { UploadDropzone } from "@/components/lectures/UploadDropzone";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { ErrorNotice } from "@/components/ui/ErrorState";
import { Field, Input } from "@/components/ui/Input";
import { useToast } from "@/components/ui/Toast";
import { useCreateCourse } from "@/hooks/useCourses";
import { useLectures } from "@/hooks/useLectures";
import { useImportHistorical } from "@/hooks/useStyle";
import { errorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";

type Step = 0 | 1 | 2;

/**
 * First-run setup.
 *
 * Style comes first on purpose. Following the obvious path — upload a lecture,
 * generate — produced a generic AI summary, because the style profile was
 * still empty. Teaching it first is what makes the very first note land.
 */
export default function OnboardingPage() {
  const router = useRouter();
  const toast = useToast();
  const [step, setStep] = useState<Step>(0);
  const [courseId, setCourseId] = useState<number | null>(null);
  const [courseName, setCourseName] = useState("");
  const [learned, setLearned] = useState<string[]>([]);

  const importHistorical = useImportHistorical();
  const createCourse = useCreateCourse();
  const { upload } = useLectures();

  const steps = [
    { title: "Teach it your style", icon: Sparkles },
    { title: "Add a course", icon: BookOpen },
    { title: "Upload a lecture", icon: FileText },
  ];

  const handleStyleFiles = async (files: File[]) => {
    try {
      const result = await importHistorical.mutateAsync(files);
      const features = Object.keys(result.aggregated_features ?? {}).length;
      setLearned([
        `Read ${result.imported_count} note${result.imported_count === 1 ? "" : "s"}`,
        features ? `Picked up ${features} style signals` : "Building your style profile",
      ]);
      if (result.skipped?.length) {
        toast.toast(`Skipped ${result.skipped.length} unreadable file(s).`, { tone: "info" });
      }
      setStep(1);
    } catch (error) {
      toast.error(errorMessage(error, "Those files couldn't be analysed."));
    }
  };

  const handleCreateCourse = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!courseName.trim()) return;
    try {
      const course = await createCourse.mutateAsync({ name: courseName.trim() });
      setCourseId(course.id);
      setStep(2);
    } catch (error) {
      toast.error(errorMessage(error, "Couldn't create that course."));
    }
  };

  const handleLectureFiles = async (files: File[]) => {
    try {
      await upload.mutateAsync({ files, courseId });
      toast.success("Uploading — you'll see it process on the course page.");
      router.push(courseId ? `/dashboard/courses/${courseId}` : "/dashboard");
    } catch (error) {
      toast.error(errorMessage(error, "That upload didn't go through."));
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Let&apos;s set you up</h1>
        <p className="mt-1 text-sm text-slate-400">
          Three quick steps. You can skip any of them and come back later.
        </p>
      </div>

      <ol className="flex items-center gap-2" aria-label="Setup progress">
        {steps.map((item, index) => {
          const done = index < step;
          const active = index === step;
          return (
            <li key={item.title} className="flex flex-1 items-center gap-2">
              <span
                className={cn(
                  "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-sm font-medium",
                  done && "border-emerald-500/40 bg-emerald-500/15 text-emerald-300",
                  active && "border-indigo-500/50 bg-indigo-500/15 text-indigo-300",
                  !done && !active && "border-slate-700 text-slate-500",
                )}
              >
                {done ? <Check className="h-4 w-4" /> : index + 1}
              </span>
              <span
                className={cn(
                  "hidden text-sm sm:block",
                  active ? "text-slate-200" : "text-slate-500",
                )}
              >
                {item.title}
              </span>
              {index < steps.length - 1 && <span className="h-px flex-1 bg-slate-800" />}
            </li>
          );
        })}
      </ol>

      {step === 0 && (
        <Card>
          <CardBody className="space-y-4">
            <div>
              <h2 className="font-semibold text-slate-100">Upload a few notes you wrote</h2>
              <p className="mt-1 text-sm text-slate-400">
                One to three is plenty. PersonaNotes reads how you structure things — headings,
                bullets, tone, how often you use tables and examples — and writes new notes to
                match. Skip this and your first notes will use a neutral style until you edit some.
              </p>
            </div>

            <UploadDropzone
              onFiles={handleStyleFiles}
              uploading={importHistorical.isPending}
              hint="Markdown, PDF or text notes you took yourself."
            />
            {importHistorical.isPending && (
              <p className="text-sm text-slate-400">Reading your notes…</p>
            )}
            {importHistorical.isError && <ErrorNotice error={importHistorical.error} />}

            <div className="flex justify-end">
              <Button variant="ghost" onClick={() => setStep(1)}>
                Skip for now
              </Button>
            </div>
          </CardBody>
        </Card>
      )}

      {step === 1 && (
        <Card>
          <CardBody className="space-y-4">
            {learned.length > 0 && (
              <div className="rounded-lg border border-emerald-500/25 bg-emerald-500/10 p-3">
                <p className="text-sm font-medium text-emerald-200">Style learned</p>
                <ul className="mt-1 space-y-0.5 text-sm text-emerald-300/90">
                  {learned.map((line) => (
                    <li key={line}>· {line}</li>
                  ))}
                </ul>
              </div>
            )}

            <div>
              <h2 className="font-semibold text-slate-100">Name your first course</h2>
              <p className="mt-1 text-sm text-slate-400">
                Courses keep each subject&apos;s lectures and notes together, and let you search or
                ask questions across a whole term.
              </p>
            </div>

            <form onSubmit={handleCreateCourse} className="space-y-4">
              <Field label="Course name" htmlFor="course-name">
                <Input
                  id="course-name"
                  autoFocus
                  placeholder="e.g. Machine Learning"
                  value={courseName}
                  onChange={(event) => setCourseName(event.target.value)}
                />
              </Field>
              {createCourse.isError && <ErrorNotice error={createCourse.error} />}
              <div className="flex justify-between">
                <Button type="button" variant="ghost" onClick={() => setStep(2)}>
                  Skip
                </Button>
                <Button type="submit" isLoading={createCourse.isPending} disabled={!courseName.trim()}>
                  Continue <ArrowRight className="h-4 w-4" />
                </Button>
              </div>
            </form>
          </CardBody>
        </Card>
      )}

      {step === 2 && (
        <Card>
          <CardBody className="space-y-4">
            <div>
              <h2 className="font-semibold text-slate-100">Add your first lecture</h2>
              <p className="mt-1 text-sm text-slate-400">
                Slides, a transcript, a reading, or a photo of a handout. This is the material your
                notes will be built from.
              </p>
            </div>

            <UploadDropzone
              onFiles={handleLectureFiles}
              uploading={upload.isPending}
              error={upload.isError ? upload.error : undefined}
            />

            <div className="flex justify-end">
              <Button variant="ghost" onClick={() => router.push("/dashboard")}>
                I&apos;ll do this later
              </Button>
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  );
}
