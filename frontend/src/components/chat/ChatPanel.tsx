"use client";

import { ArrowUp, BookmarkPlus, FileText, Plus, Sparkles, Square, StickyNote } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { Markdown } from "@/components/notes/Markdown";
import { Button } from "@/components/ui/Button";
import { ErrorNotice } from "@/components/ui/ErrorState";
import { useToast } from "@/components/ui/Toast";
import { ChatScope, LocalMessage, useChat, useChatSuggestions } from "@/hooks/useChat";
import { useSaveAnswer } from "@/hooks/useNotes";
import { errorMessage } from "@/lib/api";
import type { Citation } from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * Ask questions about your own material.
 *
 * Retrieval is scoped by where the question was asked, citations appear as soon
 * as retrieval resolves (before the answer finishes writing), and a good answer
 * can be kept as a note — otherwise a useful exchange evaporates on reload.
 */
export function ChatPanel({
  scope,
  className,
  placeholder,
  initialQuestion,
  appendTargetNoteId,
}: {
  scope: ChatScope;
  className?: string;
  placeholder?: string;
  initialQuestion?: string;
  /** When present, an answer can be appended to this note as well as saved. */
  appendTargetNoteId?: number | null;
}) {
  const { messages, send, stop, startNew, isStreaming, error } = useChat(scope);
  const { data: suggestions } = useChatSuggestions({
    noteId: scope.note_id ?? null,
    lectureId: scope.lecture_id ?? null,
  });
  const [draft, setDraft] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const sentInitial = useRef(false);

  useEffect(() => {
    if (initialQuestion && !sentInitial.current) {
      sentInitial.current = true;
      void send(initialQuestion);
    }
  }, [initialQuestion, send]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  const submit = (event?: React.FormEvent) => {
    event?.preventDefault();
    const text = draft.trim();
    if (!text || isStreaming) return;
    setDraft("");
    void send(text);
  };

  return (
    <div className={cn("flex min-h-0 flex-col", className)}>
      <div className="flex items-center justify-between gap-2 border-b border-slate-800 pb-2">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-200">
          <Sparkles className="h-4 w-4 text-indigo-400" /> Ask
        </h2>
        {messages.length > 0 && (
          <Button size="sm" variant="ghost" onClick={startNew}>
            <Plus className="h-3.5 w-3.5" /> New
          </Button>
        )}
      </div>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto py-4">
        {messages.length === 0 && (
          <div className="space-y-3">
            <p className="text-sm text-slate-400">
              Ask anything about {scopeLabel(scope)}. Answers are drawn from your own material and
              cite where they came from.
            </p>
            <ul className="space-y-1.5">
              {(suggestions ?? []).map((question) => (
                <li key={question}>
                  <button
                    type="button"
                    onClick={() => void send(question)}
                    className="w-full rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2 text-left text-sm text-slate-300 transition-colors hover:border-indigo-500/40 hover:text-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
                  >
                    {question}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            scope={scope}
            appendTargetNoteId={appendTargetNoteId}
          />
        ))}

        {error && <ErrorNotice error={error} />}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={submit} className="border-t border-slate-800 pt-3">
        <div className="flex items-end gap-2">
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) submit(event);
            }}
            rows={1}
            placeholder={placeholder ?? "Ask a question…"}
            aria-label="Your question"
            className="max-h-32 min-h-[42px] flex-1 resize-none rounded-lg border border-slate-700 bg-slate-900/50 px-3 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 focus:border-indigo-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/40"
          />
          {isStreaming ? (
            <Button type="button" variant="secondary" onClick={stop} aria-label="Stop generating">
              <Square className="h-4 w-4" />
            </Button>
          ) : (
            <Button type="submit" disabled={!draft.trim()} aria-label="Send question">
              <ArrowUp className="h-4 w-4" />
            </Button>
          )}
        </div>
      </form>
    </div>
  );
}

function scopeLabel(scope: ChatScope): string {
  switch (scope.scope) {
    case "note":
      return "this note";
    case "lecture":
      return "this lecture";
    case "course":
      return "this course";
    default:
      return "your lectures and notes";
  }
}

function MessageBubble({
  message,
  scope,
  appendTargetNoteId,
}: {
  message: LocalMessage;
  scope: ChatScope;
  appendTargetNoteId?: number | null;
}) {
  const toast = useToast();
  const saveAnswer = useSaveAnswer();

  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <p className="max-w-[85%] rounded-2xl rounded-br-sm bg-indigo-500/15 px-3.5 py-2 text-sm text-slate-100">
          {message.content}
        </p>
      </div>
    );
  }

  const save = async (append: boolean) => {
    try {
      await saveAnswer.mutateAsync({
        content: message.content,
        lecture_id: scope.lecture_id ?? null,
        course_id: scope.course_id ?? null,
        append_to_note_id: append ? appendTargetNoteId ?? null : null,
      });
      toast.success(append ? "Added to this note." : "Saved as a new note.");
    } catch (saveError) {
      toast.error(errorMessage(saveError, "Couldn't save that answer."));
    }
  };

  return (
    <div className="space-y-2">
      {message.pending && !message.content && (
        <p className="flex items-center gap-2 text-sm text-slate-500">
          <span className="h-3 w-3 animate-spin rounded-full border-2 border-indigo-400 border-t-transparent" />
          {message.citations.length > 0
            ? `Found ${message.citations.length} relevant section${message.citations.length === 1 ? "" : "s"} — writing…`
            : "Looking through your material…"}
        </p>
      )}

      {message.content && (
        <div className="rounded-2xl rounded-bl-sm bg-slate-900/60 px-3.5 py-2.5 text-sm">
          <Markdown compact>{message.content}</Markdown>
        </div>
      )}

      {message.citations.length > 0 && <Citations citations={message.citations} />}

      {!message.pending && message.content && (
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="ghost" onClick={() => save(false)} isLoading={saveAnswer.isPending}>
            <BookmarkPlus className="h-3.5 w-3.5" /> Save as note
          </Button>
          {appendTargetNoteId && (
            <Button size="sm" variant="ghost" onClick={() => save(true)}>
              Add to this note
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

function Citations({ citations }: { citations: Citation[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="text-xs">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="text-slate-500 hover:text-slate-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 rounded"
      >
        {citations.length} source{citations.length === 1 ? "" : "s"} {open ? "▴" : "▾"}
      </button>
      {open && (
        <ul className="mt-2 space-y-2">
          {citations.map((citation, index) => (
            <li key={index} className="rounded-lg border border-slate-800 bg-slate-950/60 p-2.5">
              <div className="mb-1 flex flex-wrap items-center gap-1.5 text-slate-400">
                <span className="rounded bg-slate-800 px-1 font-mono text-[10px]">{index + 1}</span>
                {/* Key off the chunk's kind, not its lecture id: a chunk from one
                    of your own notes also carries a lecture id, and showing it as
                    the source document would pass AI-written text off as the
                    original material. */}
                {citation.note_id ? (
                  <Link
                    href={`/dashboard/notes/${citation.note_id}`}
                    className="inline-flex items-center gap-1 text-emerald-400 hover:underline"
                  >
                    <StickyNote className="h-3 w-3" />
                    {citation.note_title ?? "Your notes"}
                  </Link>
                ) : citation.lecture_id ? (
                  <Link
                    href={`/dashboard/lectures/${citation.lecture_id}`}
                    className="inline-flex items-center gap-1 text-indigo-400 hover:underline"
                  >
                    <FileText className="h-3 w-3" />
                    {citation.lecture_title ?? `Lecture ${citation.lecture_id}`}
                  </Link>
                ) : (
                  <span>Your material</span>
                )}
                {citation.page ? <span>p.{citation.page}</span> : null}
              </div>
              <p className="line-clamp-4 text-slate-400">{citation.text}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
