"use client";

import {
  BookOpen,
  FileText,
  ListChecks,
  ScrollText,
  Sparkles,
  SquareStack,
  StopCircle,
  Table,
} from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { GroundingPanel } from "@/components/notes/Grounding";
import { Markdown } from "@/components/notes/Markdown";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { ErrorNotice } from "@/components/ui/ErrorState";
import { Select } from "@/components/ui/Select";
import { Skeleton } from "@/components/ui/Skeleton";
import { Textarea } from "@/components/ui/Textarea";
import { useCourses } from "@/hooks/useCourses";
import { useLectures } from "@/hooks/useLectures";
import { useStreamingGenerate } from "@/hooks/useNotes";
import type { NoteType } from "@/lib/types";
import { cn } from "@/lib/utils";

const PRESETS: {
  id: NoteType;
  label: string;
  icon: typeof ScrollText;
  description: string;
}[] = [
  { id: "full", label: "Full notes", icon: ScrollText, description: "Complete, in depth" },
  { id: "summary", label: "Summary", icon: FileText, description: "The few things that matter" },
  { id: "key_concepts", label: "Key concepts", icon: ListChecks, description: "Glossary style" },
  { id: "practice", label: "Practice questions", icon: SquareStack, description: "With answers" },
  { id: "cheatsheet", label: "Cheat sheet", icon: Table, description: "Dense, one page" },
];

const OVERRIDES: { key: string; label: string; options: { value: string; label: string }[] }[] = [
  {
    key: "length",
    label: "Length",
    options: [
      { value: "shorter", label: "Shorter" },
      { value: "longer", label: "Longer" },
    ],
  },
  {
    key: "diagrams",
    label: "Diagrams",
    options: [
      { value: "more", label: "More" },
      { value: "fewer", label: "Fewer" },
    ],
  },
  {
    key: "examples",
    label: "Examples",
    options: [
      { value: "more", label: "More" },
      { value: "fewer", label: "Fewer" },
    ],
  },
];

/**
 * Generation.
 *
 * Streamed, with retrieval reported before the first token — a 5–20 second
 * blocking call behind a single button spinner is the main reason this used to
 * feel slow. Presets replace a blank prompt box, which was a cold start.
 */
function GenerateInner() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const initialLecture = searchParams.get("lecture");
  const initialCourse = searchParams.get("course");

  const { lectures } = useLectures();
  const { data: courses } = useCourses();
  const readyLectures = lectures.filter((l) => l.ingestion_status === "ready");

  const [scope, setScope] = useState<string>(
    initialLecture ? `lecture:${initialLecture}` : initialCourse ? `course:${initialCourse}` : "all",
  );
  const [noteType, setNoteType] = useState<NoteType>("full");
  const [prompt, setPrompt] = useState("");
  const [overrides, setOverrides] = useState<Record<string, string>>({});

  const generate = useStreamingGenerate();

  // Once the note is saved it has a real URL — send the user to it rather than
  // leaving the result trapped in this page's state.
  useEffect(() => {
    if (generate.stage === "done" && generate.noteId) {
      router.push(`/dashboard/notes/${generate.noteId}`);
    }
  }, [generate.stage, generate.noteId, router]);

  const start = () => {
    const [kind, id] = scope.split(":");
    void generate.start({
      prompt: prompt.trim(),
      note_type: noteType,
      lecture_id: kind === "lecture" ? Number(id) : null,
      course_id: kind === "course" ? Number(id) : null,
      style_overrides: Object.keys(overrides).length ? overrides : null,
      no_cache: false,
    });
  };

  const toggleOverride = (key: string, value: string) =>
    setOverrides((current) => {
      const next = { ...current };
      if (next[key] === value) delete next[key];
      else next[key] = value;
      return next;
    });

  const canGenerate = noteType !== "custom" || prompt.trim().length > 0;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-bold text-slate-100">
          <Sparkles className="h-6 w-6 text-indigo-400" /> Generate notes
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          Built from your own material, written in your learned style.
        </p>
      </div>

      <Card>
        <CardBody className="space-y-5">
          <fieldset>
            <legend className="mb-2 text-sm font-medium text-slate-300">What to write</legend>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
              {PRESETS.map((preset) => {
                const Icon = preset.icon;
                const active = noteType === preset.id;
                return (
                  <button
                    key={preset.id}
                    type="button"
                    onClick={() => setNoteType(preset.id)}
                    aria-pressed={active}
                    className={cn(
                      "flex flex-col items-start gap-1 rounded-lg border p-3 text-left transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500",
                      active
                        ? "border-indigo-500/50 bg-indigo-500/10"
                        : "border-slate-800 bg-slate-900/40 hover:border-slate-700",
                    )}
                  >
                    <Icon className={cn("h-4 w-4", active ? "text-indigo-400" : "text-slate-500")} />
                    <span className="text-sm font-medium text-slate-200">{preset.label}</span>
                    <span className="text-xs text-slate-500">{preset.description}</span>
                  </button>
                );
              })}
            </div>
          </fieldset>

          <div>
            <label htmlFor="scope" className="mb-1.5 block text-sm font-medium text-slate-300">
              Source material
            </label>
            <Select id="scope" value={scope} onChange={(event) => setScope(event.target.value)}>
              <option value="all">Everything I&apos;ve uploaded</option>
              {(courses ?? []).length > 0 && (
                <optgroup label="Whole course">
                  {(courses ?? []).map((course) => (
                    <option key={`course-${course.id}`} value={`course:${course.id}`}>
                      {course.name}
                    </option>
                  ))}
                </optgroup>
              )}
              {readyLectures.length > 0 && (
                <optgroup label="One lecture">
                  {readyLectures.map((lecture) => (
                    <option key={`lecture-${lecture.id}`} value={`lecture:${lecture.id}`}>
                      {lecture.title || lecture.filename}
                    </option>
                  ))}
                </optgroup>
              )}
            </Select>
            {readyLectures.length === 0 && (
              <p className="mt-1.5 text-xs text-amber-400">
                No processed lectures yet — notes won&apos;t be grounded in your material until you
                upload one.
              </p>
            )}
          </div>

          <div>
            <label htmlFor="prompt" className="mb-1.5 block text-sm font-medium text-slate-300">
              Anything specific? <span className="text-slate-500">(optional)</span>
            </label>
            <Textarea
              id="prompt"
              rows={2}
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              placeholder="e.g. focus on backpropagation, with a worked example"
            />
          </div>

          <fieldset>
            <legend className="mb-2 text-sm font-medium text-slate-300">
              Just this once <span className="font-normal text-slate-500">— won&apos;t change your style profile</span>
            </legend>
            <div className="flex flex-wrap gap-4">
              {OVERRIDES.map((group) => (
                <div key={group.key} className="flex items-center gap-2">
                  <span className="text-xs text-slate-400">{group.label}</span>
                  <div className="flex rounded-lg border border-slate-800 p-0.5">
                    {group.options.map((option) => (
                      <button
                        key={option.value}
                        type="button"
                        onClick={() => toggleOverride(group.key, option.value)}
                        aria-pressed={overrides[group.key] === option.value}
                        className={cn(
                          "rounded px-2 py-1 text-xs transition-colors",
                          overrides[group.key] === option.value
                            ? "bg-indigo-500/20 text-indigo-300"
                            : "text-slate-400 hover:text-slate-200",
                        )}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </fieldset>

          {generate.error && <ErrorNotice error={generate.error} onRetry={start} />}

          <div className="flex justify-end gap-2">
            {generate.isStreaming ? (
              <Button variant="secondary" onClick={generate.cancel}>
                <StopCircle className="h-4 w-4" /> Stop
              </Button>
            ) : (
              <Button onClick={start} disabled={!canGenerate}>
                <Sparkles className="h-4 w-4" /> Generate
              </Button>
            )}
          </div>
        </CardBody>
      </Card>

      {generate.stage !== "idle" && (
        <Card>
          <CardHeader className="flex flex-wrap items-center gap-3">
            <StageIndicator stage={generate.stage} grounding={generate.grounding} />
          </CardHeader>
          <CardBody>
            {generate.grounding && (
              <GroundingPanel grounding={generate.grounding} className="mb-5" />
            )}
            {generate.text ? (
              <Markdown>{generate.text}</Markdown>
            ) : (
              <div className="space-y-3">
                <Skeleton className="h-6 w-2/3" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-11/12" />
                <Skeleton className="h-4 w-4/5" />
              </div>
            )}
          </CardBody>
        </Card>
      )}
    </div>
  );
}

function StageIndicator({
  stage,
  grounding,
}: {
  stage: string;
  grounding: { chunks_used: number; lecture_ids: number[] } | null;
}) {
  if (stage === "retrieving") {
    return (
      <span className="flex items-center gap-2 text-sm text-slate-300">
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-indigo-400 border-t-transparent" />
        Finding the relevant sections…
      </span>
    );
  }
  if (stage === "writing") {
    return (
      <span className="flex items-center gap-2 text-sm text-slate-300">
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-indigo-400 border-t-transparent" />
        {grounding && grounding.chunks_used > 0
          ? `Found ${grounding.chunks_used} section${grounding.chunks_used === 1 ? "" : "s"} — writing in your style…`
          : "Writing in your style…"}
      </span>
    );
  }
  if (stage === "done") {
    return (
      <span className="flex items-center gap-2 text-sm text-emerald-300">
        <BookOpen className="h-4 w-4" /> Saved — opening your note…
      </span>
    );
  }
  return <span className="text-sm text-slate-400">Generation stopped.</span>;
}

export default function GeneratePage() {
  return (
    <Suspense fallback={<Skeleton className="h-64 w-full" />}>
      <GenerateInner />
    </Suspense>
  );
}
