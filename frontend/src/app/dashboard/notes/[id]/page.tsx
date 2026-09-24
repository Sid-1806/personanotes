"use client";

import {
  ArrowLeft,
  BookOpen,
  Check,
  Download,
  FileText,
  GitCompare,
  History,
  MessageSquare,
  Pencil,
  RotateCcw,
  Sparkles,
  Trash2,
  Wand2,
  X,
} from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { ChatPanel } from "@/components/chat/ChatPanel";
import { GroundingPanel } from "@/components/notes/Grounding";
import { Markdown } from "@/components/notes/Markdown";
import { MarkdownEditor } from "@/components/notes/MarkdownEditor";
import { MobileToc, NoteToc } from "@/components/notes/NoteToc";
import { VersionsPanel } from "@/components/notes/VersionsPanel";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { ErrorNotice, ErrorPage } from "@/components/ui/ErrorState";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Skeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import {
  useDeleteNote,
  useNote,
  useRefine,
  useRevertNote,
  useSaveNote,
} from "@/hooks/useNotes";
import { API_BASE, errorMessage, getToken } from "@/lib/api";
import {
  cn,
  draftStore,
  formatDate,
  noteTypeLabel,
  readingTime,
  wordCount,
} from "@/lib/utils";

type Panel = "none" | "ask" | "versions";

/**
 * The note workspace — the product's centre of gravity.
 *
 * Every real action (edit, save, refine, teach, grounding) used to live in
 * ephemeral React state on the generate page, so a reload turned a note into a
 * read-only artifact with no actions at all. Here they hang off a durable,
 * linkable URL, and the user's own saved version is what you see by default.
 */
export default function NoteWorkspace() {
  const params = useParams();
  const router = useRouter();
  const toast = useToast();
  const noteId = Number(params?.id);

  const { data: note, isLoading, isError, error, refetch } = useNote(noteId);
  const saveNote = useSaveNote();
  const refine = useRefine();
  const revert = useRevertNote();
  const deleteNote = useDeleteNote();

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [showOriginal, setShowOriginal] = useState(false);
  const [panel, setPanel] = useState<Panel>("none");
  const [refineText, setRefineText] = useState("");
  const [selection, setSelection] = useState<string>("");
  const [renaming, setRenaming] = useState(false);
  const [titleDraft, setTitleDraft] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [teach, setTeach] = useState(true);
  const restoredDraft = useRef(false);

  const body = useMemo(() => {
    if (!note) return "";
    if (showOriginal) return note.original_markdown;
    return note.edited_markdown ?? note.original_markdown;
  }, [note, showOriginal]);

  // Recover an unsaved draft after a reload or a session timeout.
  useEffect(() => {
    if (!note || restoredDraft.current) return;
    restoredDraft.current = true;
    const saved = draftStore.read(note.id);
    if (saved && saved !== (note.edited_markdown ?? note.original_markdown)) {
      setDraft(saved);
      setEditing(true);
      toast.toast("Restored an unsaved draft from earlier.", { tone: "info" });
    }
  }, [note, toast]);

  useEffect(() => {
    if (editing && note) draftStore.write(note.id, draft);
  }, [draft, editing, note]);

  if (isError) return <ErrorPage error={error} onRetry={() => refetch()} />;
  if (isLoading || !note) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  const startEditing = () => {
    setDraft(note.edited_markdown ?? note.original_markdown);
    setShowOriginal(false);
    setEditing(true);
  };

  const cancelEditing = () => {
    setEditing(false);
    draftStore.clear(note.id);
  };

  // Saving always persists. Teaching is a separate, explainable side effect —
  // conflating them is how edits used to be stored but never readable again.
  const save = async () => {
    try {
      await saveNote.mutateAsync({ noteId: note.id, markdown: draft, teach });
      draftStore.clear(note.id);
      setEditing(false);
      toast.success(
        teach ? "Saved — and PersonaNotes learned from your changes." : "Saved.",
      );
    } catch (saveError) {
      toast.error(errorMessage(saveError, "Couldn't save your changes."));
    }
  };

  const doRefine = async (instruction?: string, passage?: string) => {
    const text = (instruction ?? refineText).trim();
    if (!text) return;
    try {
      const result = await refine.mutateAsync({
        noteId: note.id,
        instruction: text,
        selection: passage || selection || undefined,
      });
      setRefineText("");
      setSelection("");
      toast.success("Revised — saved as a new version.");
      router.push(`/dashboard/notes/${result.id}`);
    } catch (refineError) {
      toast.error(errorMessage(refineError, "That revision didn't work."));
    }
  };

  const doRevert = async () => {
    try {
      await revert.mutateAsync(note.id);
      toast.success("Reverted to the generated version.");
    } catch (revertError) {
      toast.error(errorMessage(revertError, "Couldn't revert."));
    }
  };

  const doDelete = async () => {
    try {
      await deleteNote.mutateAsync(note.id);
      toast.success("Note deleted.");
      router.push("/dashboard/notes");
    } catch (deleteError) {
      toast.error(errorMessage(deleteError, "Couldn't delete that note."));
    }
  };

  const saveTitle = async () => {
    try {
      await saveNote.mutateAsync({ noteId: note.id, title: titleDraft.trim() });
      setRenaming(false);
      toast.success("Renamed.");
    } catch (renameError) {
      toast.error(errorMessage(renameError, "Couldn't rename that."));
    }
  };

  const exportNote = () => {
    const token = getToken();
    const url = `${API_BASE}/notes/${note.id}/export`;
    // The export route needs the auth header, so fetch then hand over a blob.
    fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((response) => response.blob())
      .then((blob) => {
        const href = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = href;
        link.download = `${note.title ?? `note-${note.id}`}.md`;
        link.click();
        URL.revokeObjectURL(href);
      })
      .catch(() => toast.error("Couldn't download that note."));
  };

  const captureSelection = () => {
    const text = window.getSelection()?.toString().trim() ?? "";
    // Very short selections are usually accidental clicks, not a passage.
    setSelection(text.length > 40 ? text : "");
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3 text-sm text-slate-400">
        <Link
          href="/dashboard/notes"
          className="inline-flex items-center gap-1.5 hover:text-slate-200"
        >
          <ArrowLeft className="h-4 w-4" /> Notes
        </Link>
        {note.course_id && note.course_name && (
          <>
            <span className="text-slate-700">/</span>
            <Link
              href={`/dashboard/courses/${note.course_id}`}
              className="inline-flex items-center gap-1.5 hover:text-slate-200"
            >
              <BookOpen className="h-3.5 w-3.5" /> {note.course_name}
            </Link>
          </>
        )}
        {note.lecture_id && note.lecture_title && (
          <>
            <span className="text-slate-700">/</span>
            <Link
              href={`/dashboard/lectures/${note.lecture_id}`}
              className="inline-flex min-w-0 items-center gap-1.5 hover:text-slate-200"
            >
              <FileText className="h-3.5 w-3.5 shrink-0" />
              <span className="truncate">{note.lecture_title}</span>
            </Link>
          </>
        )}
      </div>

      <header className="space-y-3">
        {renaming ? (
          <div className="flex flex-wrap items-center gap-2">
            <Input
              value={titleDraft}
              onChange={(event) => setTitleDraft(event.target.value)}
              className="max-w-md"
              aria-label="Note title"
              autoFocus
            />
            <Button size="sm" onClick={saveTitle} isLoading={saveNote.isPending}>
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
              setTitleDraft(note.title ?? "");
              setRenaming(true);
            }}
            title="Click to rename"
            className="rounded text-left text-2xl font-bold tracking-tight text-slate-100 hover:text-indigo-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 sm:text-3xl"
          >
            {note.title ?? `Notes ${note.id}`}
          </button>
        )}

        <div className="flex flex-wrap items-center gap-2 text-sm text-slate-400">
          <Badge tone="neutral">{noteTypeLabel(note.note_type)}</Badge>
          <span>{formatDate(note.created_at)}</span>
          <span>·</span>
          <span>{readingTime(wordCount(body))}</span>
          {note.has_edits && (
            <Badge tone="info">
              <Pencil className="h-3 w-3" /> You edited this
            </Badge>
          )}
          {note.version_count > 1 && (
            <Badge tone="neutral">
              {note.version_count} version{note.version_count === 1 ? "" : "s"}
            </Badge>
          )}
        </div>

        <div className="no-print flex flex-wrap gap-2">
          {!editing ? (
            <>
              <Button size="sm" onClick={startEditing}>
                <Pencil className="h-4 w-4" /> Edit
              </Button>
              <Button
                size="sm"
                variant={panel === "ask" ? "primary" : "secondary"}
                onClick={() => setPanel(panel === "ask" ? "none" : "ask")}
              >
                <MessageSquare className="h-4 w-4" /> Ask
              </Button>
              <Button
                size="sm"
                variant={panel === "versions" ? "primary" : "secondary"}
                onClick={() => setPanel(panel === "versions" ? "none" : "versions")}
              >
                <History className="h-4 w-4" /> Versions
              </Button>
              {note.has_edits && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setShowOriginal((value) => !value)}
                >
                  <GitCompare className="h-4 w-4" />
                  {showOriginal ? "Show my version" : "Show original"}
                </Button>
              )}
              <Button size="sm" variant="ghost" onClick={exportNote}>
                <Download className="h-4 w-4" /> Export
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setConfirmDelete(true)}>
                <Trash2 className="h-4 w-4" />
              </Button>
            </>
          ) : (
            <>
              <Button size="sm" onClick={save} isLoading={saveNote.isPending}>
                <Check className="h-4 w-4" /> Save
              </Button>
              <Button size="sm" variant="ghost" onClick={cancelEditing}>
                <X className="h-4 w-4" /> Cancel
              </Button>
              <label className="flex items-center gap-2 text-sm text-slate-400">
                <input
                  type="checkbox"
                  checked={teach}
                  onChange={(event) => setTeach(event.target.checked)}
                  className="h-4 w-4 rounded border-slate-600 accent-indigo-500"
                />
                Learn from these changes
              </label>
            </>
          )}
        </div>
      </header>

      {showOriginal && note.has_edits && (
        <div className="rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-2 text-sm text-slate-300">
          Showing the originally generated text. Your saved version is unchanged.
        </div>
      )}

      <GroundingPanel grounding={note.grounding} className="no-print" />

      <div
        className={cn(
          "grid gap-6",
          panel !== "none" ? "xl:grid-cols-[minmax(0,1fr)_360px]" : "lg:grid-cols-[200px_minmax(0,1fr)]",
        )}
      >
        {panel === "none" && !editing && (
          <aside className="no-print hidden lg:block">
            <div className="sticky top-24">
              <NoteToc markdown={body} />
            </div>
          </aside>
        )}

        <main className="min-w-0">
          {editing ? (
            <>
              <MarkdownEditor
                value={draft}
                onChange={setDraft}
                onSave={save}
                saving={saveNote.isPending}
                autoFocus
              />
              {saveNote.isError && <ErrorNotice error={saveNote.error} className="mt-3" />}
            </>
          ) : (
            <article onMouseUp={captureSelection} onTouchEnd={captureSelection}>
              <Markdown>{body}</Markdown>
            </article>
          )}

          {!editing && (
            <div className="no-print mt-8 space-y-3 border-t border-slate-800 pt-5">
              {selection && (
                <div className="flex flex-wrap items-center gap-2 rounded-lg border border-indigo-500/25 bg-indigo-500/10 px-3 py-2 text-sm text-indigo-200">
                  <Wand2 className="h-4 w-4 shrink-0" />
                  <span className="min-w-0 flex-1 truncate">
                    Revising just the selected passage
                  </span>
                  <button
                    type="button"
                    onClick={() => setSelection("")}
                    className="shrink-0 text-xs underline"
                  >
                    Use whole note
                  </button>
                </div>
              )}

              <div className="flex flex-col gap-2 sm:flex-row">
                <input
                  value={refineText}
                  onChange={(event) => setRefineText(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") void doRefine();
                  }}
                  placeholder={
                    selection
                      ? "How should this passage change?"
                      : "Refine — e.g. “add a worked example” or “make it more concise”"
                  }
                  aria-label="Refine instruction"
                  className="w-full rounded-lg border border-slate-700 bg-slate-900/50 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-indigo-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/40"
                />
                <Button
                  onClick={() => void doRefine()}
                  isLoading={refine.isPending}
                  disabled={!refineText.trim()}
                  className="shrink-0"
                >
                  <Wand2 className="h-4 w-4" /> Refine
                </Button>
              </div>

              {refine.isError && <ErrorNotice error={refine.error} />}

              {note.has_edits && (
                <Button size="sm" variant="ghost" onClick={doRevert} isLoading={revert.isPending}>
                  <RotateCcw className="h-4 w-4" /> Discard my edits
                </Button>
              )}
            </div>
          )}
        </main>

        {panel !== "none" && (
          <aside className="no-print min-w-0">
            <Card className="xl:sticky xl:top-24">
              <CardHeader className="flex items-center justify-between">
                <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-200">
                  {panel === "ask" ? (
                    <>
                      <Sparkles className="h-4 w-4 text-indigo-400" /> Ask about this note
                    </>
                  ) : (
                    <>
                      <History className="h-4 w-4 text-indigo-400" /> Version history
                    </>
                  )}
                </h2>
                <button
                  type="button"
                  onClick={() => setPanel("none")}
                  aria-label="Close panel"
                  className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                >
                  <X className="h-4 w-4" />
                </button>
              </CardHeader>
              <CardBody>
                {panel === "ask" ? (
                  <ChatPanel
                    scope={{
                      scope: "note",
                      note_id: note.id,
                      lecture_id: note.lecture_id,
                      course_id: note.course_id,
                    }}
                    className="h-[60vh]"
                    appendTargetNoteId={note.id}
                    placeholder="Ask about this note…"
                  />
                ) : (
                  <VersionsPanel noteId={note.id} />
                )}
              </CardBody>
            </Card>
          </aside>
        )}
      </div>

      {!editing && <MobileToc markdown={body} />}

      <Modal
        open={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        title="Delete this note?"
        description="This removes the note, your edits and its search index. It can't be undone."
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirmDelete(false)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={doDelete} isLoading={deleteNote.isPending}>
              <Trash2 className="h-4 w-4" /> Delete
            </Button>
          </>
        }
      />
    </div>
  );
}
