"use client";

import {
  BookOpen,
  CornerDownLeft,
  FileText,
  MessageSquare,
  Search,
  Sparkles,
  StickyNote,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { useJump } from "@/hooks/useSearch";
import { useDebounced } from "@/hooks/useDebounced";
import { cn } from "@/lib/utils";

interface Command {
  id: string;
  label: string;
  hint?: string;
  icon: typeof Search;
  run: () => void;
}

/**
 * ⌘K palette: search the corpus and jump to any course, lecture or note.
 *
 * With courses and notes both growing over a term, hunting through nav menus
 * stops scaling — this is the constant-time way to get anywhere.
 */
export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState(0);
  const debounced = useDebounced(query, 180);
  const { data: matches } = useJump(debounced);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setCursor(0);
    }
  }, [open]);

  const go = useMemo(
    () => (href: string) => {
      onClose();
      router.push(href);
    },
    [onClose, router],
  );

  const commands = useMemo<Command[]>(() => {
    const actions: Command[] = [];
    const trimmed = query.trim();

    if (trimmed) {
      actions.push({
        id: "search",
        label: `Search for "${trimmed}"`,
        hint: "Across lectures and notes",
        icon: Search,
        run: () => go(`/dashboard/search?q=${encodeURIComponent(trimmed)}`),
      });
      actions.push({
        id: "ask",
        label: `Ask "${trimmed}"`,
        hint: "Answered from your material",
        icon: MessageSquare,
        run: () => go(`/dashboard/ask?q=${encodeURIComponent(trimmed)}`),
      });
    } else {
      actions.push(
        { id: "nav-courses", label: "Go to Courses", icon: BookOpen, run: () => go("/dashboard/courses") },
        { id: "nav-notes", label: "Go to Notes", icon: StickyNote, run: () => go("/dashboard/notes") },
        { id: "nav-ask", label: "Ask a question", icon: MessageSquare, run: () => go("/dashboard/ask") },
        { id: "nav-style", label: "Style profile", icon: Sparkles, run: () => go("/dashboard/style") },
      );
    }

    for (const match of matches ?? []) {
      const href =
        match.kind === "course"
          ? `/dashboard/courses/${match.id}`
          : match.kind === "lecture"
            ? `/dashboard/lectures/${match.id}`
            : `/dashboard/notes/${match.id}`;
      actions.push({
        id: `${match.kind}-${match.id}`,
        label: match.title,
        hint: match.kind === "course" ? "Course" : match.kind === "lecture" ? "Lecture" : "Note",
        icon: match.kind === "course" ? BookOpen : match.kind === "lecture" ? FileText : StickyNote,
        run: () => go(href),
      });
    }

    return actions;
  }, [go, matches, query]);

  useEffect(() => {
    setCursor(0);
  }, [debounced]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      } else if (event.key === "ArrowDown") {
        event.preventDefault();
        setCursor((c) => Math.min(c + 1, commands.length - 1));
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        setCursor((c) => Math.max(c - 1, 0));
      } else if (event.key === "Enter") {
        event.preventDefault();
        commands[cursor]?.run();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [commands, cursor, onClose, open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[95] flex items-start justify-center p-4 pt-[12vh]">
      <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" onClick={onClose} aria-hidden />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        className="relative w-full max-w-xl overflow-hidden rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl"
      >
        <div className="flex items-center gap-3 border-b border-slate-800 px-4">
          <Search className="h-4 w-4 shrink-0 text-slate-500" />
          <input
            autoFocus
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search, ask, or jump to…"
            aria-label="Search, ask, or jump to"
            className="w-full bg-transparent py-3.5 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none"
          />
        </div>

        <ul className="max-h-80 overflow-y-auto p-2">
          {commands.length === 0 && (
            <li className="px-3 py-6 text-center text-sm text-slate-500">Nothing matched.</li>
          )}
          {commands.map((command, index) => {
            const Icon = command.icon;
            return (
              <li key={command.id}>
                <button
                  type="button"
                  onMouseEnter={() => setCursor(index)}
                  onClick={command.run}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition-colors",
                    index === cursor ? "bg-slate-800 text-slate-100" : "text-slate-300",
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0 text-slate-500" />
                  <span className="flex-1 truncate">{command.label}</span>
                  {command.hint && (
                    <span className="hidden shrink-0 text-xs text-slate-500 sm:block">
                      {command.hint}
                    </span>
                  )}
                  {index === cursor && <CornerDownLeft className="h-3.5 w-3.5 shrink-0 text-slate-600" />}
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
