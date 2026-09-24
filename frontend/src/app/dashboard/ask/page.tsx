"use client";

import { MessageSquare, Plus, Trash2 } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";

import { ChatPanel } from "@/components/chat/ChatPanel";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { Skeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { useChatThreads, useDeleteThread } from "@/hooks/useChat";
import { useCourses } from "@/hooks/useCourses";
import { useLectures } from "@/hooks/useLectures";
import type { Scope } from "@/lib/types";
import { cn, relativeTime } from "@/lib/utils";

/**
 * Standalone Ask.
 *
 * Asking a question used to require generating a whole note; this is the
 * lighter path, and past conversations persist so a thread survives a reload.
 */
function AskInner() {
  const searchParams = useSearchParams();
  const toast = useToast();

  const initialQuestion = searchParams.get("q") ?? undefined;
  const initialLecture = searchParams.get("lecture");
  const initialCourse = searchParams.get("course");

  const [scopeValue, setScopeValue] = useState<string>(
    initialLecture ? `lecture:${initialLecture}` : initialCourse ? `course:${initialCourse}` : "all",
  );
  // Remounts the panel on scope change so a new conversation starts cleanly.
  const [sessionKey, setSessionKey] = useState(0);

  const { data: courses } = useCourses();
  const { lectures } = useLectures();
  const readyLectures = lectures.filter((l) => l.ingestion_status === "ready");

  const { data: threads } = useChatThreads();
  const deleteThread = useDeleteThread();

  const scope = useMemo(() => {
    const [kind, id] = scopeValue.split(":");
    if (kind === "lecture") {
      const lecture = lectures.find((l) => l.id === Number(id));
      return {
        scope: "lecture" as Scope,
        lecture_id: Number(id),
        course_id: lecture?.course_id ?? null,
      };
    }
    if (kind === "course") return { scope: "course" as Scope, course_id: Number(id) };
    return { scope: "all" as Scope };
  }, [scopeValue, lectures]);

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
      <div className="space-y-4">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-slate-100">
            <MessageSquare className="h-6 w-6 text-indigo-400" /> Ask
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Answers come from your own lectures and notes, with citations you can check.
          </p>
        </div>

        <Select
          value={scopeValue}
          onChange={(event) => {
            setScopeValue(event.target.value);
            setSessionKey((key) => key + 1);
          }}
          aria-label="What to ask about"
        >
          <option value="all">Everything I&apos;ve uploaded</option>
          {(courses ?? []).length > 0 && (
            <optgroup label="One course">
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

        <Card>
          <CardBody>
            <ChatPanel
              key={sessionKey}
              scope={scope}
              className="h-[65vh]"
              initialQuestion={sessionKey === 0 ? initialQuestion : undefined}
            />
          </CardBody>
        </Card>
      </div>

      <aside className="min-w-0">
        <Card>
          <CardHeader className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-200">Recent conversations</h2>
            <Button size="sm" variant="ghost" onClick={() => setSessionKey((key) => key + 1)}>
              <Plus className="h-3.5 w-3.5" /> New
            </Button>
          </CardHeader>
          <CardBody className="p-0">
            {!threads?.length ? (
              <p className="px-5 py-6 text-sm text-slate-400">
                Your past questions will be listed here.
              </p>
            ) : (
              <ul className="divide-y divide-slate-800">
                {threads.map((thread) => (
                  <li
                    key={thread.id}
                    className={cn("flex items-start gap-2 px-4 py-3 hover:bg-slate-800/40")}
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm text-slate-200">{thread.title}</p>
                      <p className="text-xs text-slate-500">
                        {thread.message_count} message{thread.message_count === 1 ? "" : "s"} ·{" "}
                        {relativeTime(thread.updated_at ?? thread.created_at)}
                      </p>
                    </div>
                    <button
                      type="button"
                      aria-label={`Delete conversation: ${thread.title}`}
                      onClick={async () => {
                        try {
                          await deleteThread.mutateAsync(thread.id);
                          toast.success("Conversation deleted.");
                        } catch {
                          toast.error("Couldn't delete that conversation.");
                        }
                      }}
                      className="shrink-0 rounded p-1 text-slate-500 hover:bg-slate-800 hover:text-rose-400"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>
      </aside>
    </div>
  );
}

export default function AskPage() {
  return (
    <Suspense fallback={<Skeleton className="h-64 w-full" />}>
      <AskInner />
    </Suspense>
  );
}
