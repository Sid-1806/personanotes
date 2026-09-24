"use client";

import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  Check,
  FileText,
  MessageSquare,
  RefreshCw,
  Sparkles,
  StickyNote,
  TrendingDown,
  UploadCloud,
} from "lucide-react";
import Link from "next/link";
import { ReactNode } from "react";

import { StatusBadge } from "@/components/lectures/LectureRow";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { ErrorPage } from "@/components/ui/ErrorState";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { Skeleton } from "@/components/ui/Skeleton";
import { useAuth } from "@/hooks/useAuth";
import { useDashboardSummary } from "@/hooks/useDashboard";
import { useLectures } from "@/hooks/useLectures";
import { noteTypeLabel, relativeTime } from "@/lib/utils";

/**
 * Home.
 *
 * Answers "what should I do next?" rather than showing counters. A brand-new
 * account gets a setup checklist instead of "Welcome back" over a wall of
 * zeroes; an established one gets failures, un-noted lectures and weak topics.
 */
export default function DashboardPage() {
  const { user } = useAuth();
  const { data: summary, isLoading, isError, error, refetch } = useDashboardSummary();
  const { retry } = useLectures();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-9 w-64" />
        <div className="grid gap-4 sm:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (isError) return <ErrorPage error={error} onRetry={() => refetch()} />;
  if (!summary) return null;

  const firstName = user?.name?.split(" ")[0];
  const onboarding = summary.onboarding;

  if (!onboarding.complete) {
    return <GettingStarted firstName={firstName} onboarding={onboarding} />;
  }

  const { personalization_metrics: metrics } = summary;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">
          Welcome back{firstName ? `, ${firstName}` : ""}
        </h1>
        <p className="mt-1 text-sm text-slate-400">Here&apos;s where to pick things up.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <QuickAction
          href="/dashboard/courses"
          icon={<UploadCloud className="h-5 w-5" />}
          title="Add material"
          subtitle="Upload into a course"
        />
        <QuickAction
          href="/dashboard/generate"
          icon={<Sparkles className="h-5 w-5" />}
          title="Generate notes"
          subtitle="Grounded and personalized"
        />
        <QuickAction
          href="/dashboard/ask"
          icon={<MessageSquare className="h-5 w-5" />}
          title="Ask a question"
          subtitle="Answered from your material"
        />
      </div>

      {summary.needs_attention.length > 0 && (
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-slate-200">Needs attention</h2>
          </CardHeader>
          <CardBody className="p-0">
            <ul className="divide-y divide-slate-800">
              {summary.needs_attention.map((item) => (
                <li
                  key={`${item.type}-${item.lecture_id}`}
                  className="flex flex-wrap items-center gap-3 px-5 py-3"
                >
                  <span className="shrink-0">
                    {item.type === "lecture_failed" ? (
                      <AlertTriangle className="h-4 w-4 text-rose-400" />
                    ) : (
                      <FileText className="h-4 w-4 text-indigo-400" />
                    )}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm text-slate-200">{item.title}</p>
                    <p className="truncate text-xs text-slate-400">{item.detail}</p>
                  </div>
                  {item.type === "lecture_failed" ? (
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => retry.mutate(item.lecture_id)}
                      isLoading={retry.isPending && retry.variables === item.lecture_id}
                    >
                      <RefreshCw className="h-3.5 w-3.5" /> Retry
                    </Button>
                  ) : (
                    <Link href={`/dashboard/generate?lecture=${item.lecture_id}`}>
                      <Button size="sm" variant="secondary">
                        <Sparkles className="h-3.5 w-3.5" /> Generate
                      </Button>
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-200">Recent notes</h2>
              <Link href="/dashboard/notes" className="text-sm text-indigo-400 hover:underline">
                View all
              </Link>
            </CardHeader>
            <CardBody className="p-0">
              {summary.recent_notes.length === 0 ? (
                <p className="px-5 py-8 text-sm text-slate-400">
                  Notes you generate will appear here.
                </p>
              ) : (
                <ul className="divide-y divide-slate-800">
                  {summary.recent_notes.map((note) => (
                    <li key={note.id}>
                      <Link
                        href={`/dashboard/notes/${note.id}`}
                        className="flex items-center gap-3 px-5 py-3 hover:bg-slate-800/40"
                      >
                        <StickyNote className="h-4 w-4 shrink-0 text-slate-500" />
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm text-slate-200">
                            {note.title ?? `Notes for ${note.lecture_filename ?? "your prompt"}`}
                          </p>
                          <p className="truncate text-xs text-slate-400">
                            {[
                              noteTypeLabel(note.note_type),
                              note.course_name,
                              relativeTime(note.created_at),
                            ]
                              .filter(Boolean)
                              .join(" · ")}
                          </p>
                        </div>
                        <ArrowRight className="h-4 w-4 shrink-0 text-slate-600" />
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-200">Recent lectures</h2>
              <Link href="/dashboard/courses" className="text-sm text-indigo-400 hover:underline">
                All courses
              </Link>
            </CardHeader>
            <CardBody className="p-0">
              {summary.recent_lectures.length === 0 ? (
                <p className="px-5 py-8 text-sm text-slate-400">No lectures uploaded yet.</p>
              ) : (
                <ul className="divide-y divide-slate-800">
                  {summary.recent_lectures.map((lecture) => (
                    <li key={lecture.id}>
                      <Link
                        href={`/dashboard/lectures/${lecture.id}`}
                        className="flex flex-wrap items-center justify-between gap-2 px-5 py-3 hover:bg-slate-800/40"
                      >
                        <span className="flex min-w-0 items-center gap-3">
                          <FileText className="h-4 w-4 shrink-0 text-slate-500" />
                          <span className="truncate text-sm text-slate-200">
                            {lecture.title ?? lecture.filename}
                          </span>
                        </span>
                        <StatusBadge
                          lecture={{
                            ingestion_status: lecture.status,
                            chunk_count: lecture.chunk_count,
                          }}
                        />
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <h2 className="text-sm font-semibold text-slate-200">Personalization</h2>
            </CardHeader>
            <CardBody>
              <p className="text-4xl font-bold text-slate-100">
                {Math.round(metrics.current_score)}%
              </p>
              <div className="mt-3">
                <ProgressBar value={metrics.current_score / 100} />
              </div>
              <p className="mt-2 text-xs text-slate-400">
                {metrics.measured
                  ? "How closely your last generated note matched your style."
                  : "Edit a generated note to start measuring this properly."}
              </p>
              {metrics.trend !== 0 && (
                <p className="mt-2 text-xs text-slate-400">
                  {metrics.trend > 0 ? "▲" : "▼"} {Math.abs(metrics.trend)} points since you started.
                </p>
              )}
              <Link href="/dashboard/style">
                <Button variant="ghost" size="sm" className="mt-4 w-full">
                  View style profile
                </Button>
              </Link>
            </CardBody>
          </Card>

          {summary.weak_topics.length > 0 && (
            <Card>
              <CardHeader>
                <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-200">
                  <TrendingDown className="h-4 w-4 text-amber-400" /> Worth revisiting
                </h2>
              </CardHeader>
              <CardBody className="space-y-2">
                <p className="text-xs text-slate-400">
                  You rewrote these the most, so they were the furthest from what you wanted.
                </p>
                <ul className="space-y-1.5">
                  {summary.weak_topics.map((topic) => (
                    <li key={topic.note_id}>
                      <Link
                        href={`/dashboard/notes/${topic.note_id}`}
                        className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm text-slate-300 hover:bg-slate-800/60"
                      >
                        <span className="min-w-0 flex-1 truncate">{topic.title}</span>
                        <Badge tone="warning">{topic.score}%</Badge>
                      </Link>
                    </li>
                  ))}
                </ul>
              </CardBody>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

function GettingStarted({
  firstName,
  onboarding,
}: {
  firstName?: string;
  onboarding: { has_style: boolean; has_course: boolean; has_lecture: boolean; has_note: boolean };
}) {
  const steps = [
    {
      done: onboarding.has_style,
      title: "Teach it your style",
      body: "Upload one to three notes you wrote yourself. This is what makes the output yours.",
      href: "/dashboard/style?tab=sources",
      cta: "Add past notes",
    },
    {
      done: onboarding.has_course,
      title: "Create a course",
      body: "Group each subject's lectures and notes together.",
      href: "/dashboard/courses",
      cta: "Create a course",
    },
    {
      done: onboarding.has_lecture,
      title: "Upload a lecture",
      body: "Slides, a transcript, a reading, or a photo of a handout.",
      href: "/dashboard/courses",
      cta: "Upload material",
    },
    {
      done: onboarding.has_note,
      title: "Generate your first notes",
      body: "Grounded in your material, written in your style.",
      href: "/dashboard/generate",
      cta: "Generate notes",
    },
  ];
  const next = steps.find((step) => !step.done);

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">
          {firstName ? `Welcome, ${firstName}` : "Welcome to PersonaNotes"}
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          Four steps to notes that read like yours. {steps.filter((s) => s.done).length} of{" "}
          {steps.length} done.
        </p>
      </div>

      <ul className="space-y-3">
        {steps.map((step) => (
          <li key={step.title}>
            <Card
              className={
                step === next ? "border-indigo-500/40" : step.done ? "opacity-60" : undefined
              }
            >
              <CardBody className="flex flex-wrap items-start gap-4">
                <span
                  className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border ${
                    step.done
                      ? "border-emerald-500/40 bg-emerald-500/15 text-emerald-300"
                      : "border-slate-700 text-slate-500"
                  }`}
                >
                  {step.done ? <Check className="h-4 w-4" /> : <BookOpen className="h-3.5 w-3.5" />}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-slate-100">{step.title}</p>
                  <p className="mt-0.5 text-sm text-slate-400">{step.body}</p>
                </div>
                {!step.done && (
                  <Link href={step.href} className="shrink-0">
                    <Button size="sm" variant={step === next ? "primary" : "secondary"}>
                      {step.cta}
                    </Button>
                  </Link>
                )}
              </CardBody>
            </Card>
          </li>
        ))}
      </ul>
    </div>
  );
}

function QuickAction({
  href,
  icon,
  title,
  subtitle,
}: {
  href: string;
  icon: ReactNode;
  title: string;
  subtitle: string;
}) {
  return (
    <Link
      href={href}
      className="group flex items-center gap-4 rounded-xl border border-slate-800 bg-slate-900/60 p-5 transition-colors hover:border-indigo-500/50 hover:bg-slate-800/50 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
    >
      <span className="rounded-lg bg-indigo-500/10 p-3 text-indigo-400">{icon}</span>
      <span className="min-w-0">
        <span className="block font-medium text-slate-100">{title}</span>
        <span className="block text-xs text-slate-400">{subtitle}</span>
      </span>
      <ArrowRight className="ml-auto h-4 w-4 shrink-0 text-slate-600 transition-transform group-hover:translate-x-0.5 group-hover:text-slate-400" />
    </Link>
  );
}
