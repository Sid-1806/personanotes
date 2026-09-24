"use client";

import { Columns2, Eye, Pencil } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { Markdown } from "@/components/notes/Markdown";
import { cn, wordCount } from "@/lib/utils";

type Mode = "write" | "split" | "preview";

/**
 * Split markdown editor.
 *
 * Replaces a bare `rows={22}` monospace textarea: you can see what you're
 * producing, ⌘S saves without reaching for the mouse, and the draft is handed
 * up on every keystroke so it can survive a reload or a session timeout.
 */
export function MarkdownEditor({
  value,
  onChange,
  onSave,
  saving = false,
  autoFocus = false,
  className,
}: {
  value: string;
  onChange: (value: string) => void;
  onSave?: () => void;
  saving?: boolean;
  autoFocus?: boolean;
  className?: string;
}) {
  // Split needs width; a phone gets write/preview toggling instead.
  const [mode, setMode] = useState<Mode>("write");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.matchMedia("(min-width: 1024px)").matches) setMode("split");
  }, []);

  useEffect(() => {
    if (autoFocus) textareaRef.current?.focus();
  }, [autoFocus]);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "s") {
        event.preventDefault();
        onSave?.();
        return;
      }
      // Tab should indent inside the editor, not escape to the next control.
      if (event.key === "Tab") {
        event.preventDefault();
        const target = event.currentTarget;
        const { selectionStart, selectionEnd } = target;
        const next = `${value.slice(0, selectionStart)}  ${value.slice(selectionEnd)}`;
        onChange(next);
        requestAnimationFrame(() => {
          target.selectionStart = target.selectionEnd = selectionStart + 2;
        });
      }
    },
    [onChange, onSave, value],
  );

  const modes: { id: Mode; label: string; icon: typeof Pencil; desktopOnly?: boolean }[] = [
    { id: "write", label: "Write", icon: Pencil },
    { id: "split", label: "Split", icon: Columns2, desktopOnly: true },
    { id: "preview", label: "Preview", icon: Eye },
  ];

  return (
    <div className={cn("flex min-h-0 flex-col", className)}>
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="flex rounded-lg border border-slate-800 bg-slate-900/60 p-0.5">
          {modes.map(({ id, label, icon: Icon, desktopOnly }) => (
            <button
              key={id}
              type="button"
              onClick={() => setMode(id)}
              aria-pressed={mode === id}
              className={cn(
                "flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500",
                desktopOnly && "hidden lg:flex",
                mode === id
                  ? "bg-slate-800 text-slate-100"
                  : "text-slate-400 hover:text-slate-200",
              )}
            >
              <Icon className="h-3.5 w-3.5" />
              {label}
            </button>
          ))}
        </div>
        <span className="text-xs text-slate-400">
          {wordCount(value).toLocaleString()} words
          {saving && " · saving…"}
          {onSave && !saving && (
            <span className="ml-2 hidden sm:inline text-slate-500">⌘S to save</span>
          )}
        </span>
      </div>

      <div
        className={cn(
          "grid min-h-0 flex-1 gap-3",
          mode === "split" ? "lg:grid-cols-2" : "grid-cols-1",
        )}
      >
        {mode !== "preview" && (
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={handleKeyDown}
            spellCheck
            aria-label="Note markdown"
            className="min-h-[360px] w-full resize-y rounded-lg border border-slate-800 bg-slate-950/60 p-4 font-mono text-[13px] leading-relaxed text-slate-200 placeholder:text-slate-600 focus:border-indigo-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/40"
            placeholder="Write your notes in markdown…"
          />
        )}
        {mode !== "write" && (
          <div className="min-h-[360px] overflow-y-auto rounded-lg border border-slate-800 bg-slate-900/40 p-4">
            {value.trim() ? (
              <Markdown>{value}</Markdown>
            ) : (
              <p className="text-sm text-slate-500">Nothing to preview yet.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
