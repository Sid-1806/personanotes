import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";

import api, { ApiError } from "@/lib/api";
import { streamRequest } from "@/lib/sse";
import type {
  FeedbackResponse,
  GenerateArgs,
  GenerateResponse,
  Grounding,
  NoteDetail,
  NoteDiff,
  NoteList,
  NoteVersions,
} from "@/lib/types";

export const notesKey = ["notes"] as const;

export interface NoteFilters {
  courseId?: number | null;
  lectureId?: number | null;
  noteType?: string | null;
  q?: string;
  rootsOnly?: boolean;
  limit?: number;
  offset?: number;
}

export function useNotes(filters: NoteFilters = {}) {
  return useQuery<NoteList>({
    queryKey: [...notesKey, filters],
    queryFn: async () =>
      (
        await api.get("/notes/", {
          params: {
            course_id: filters.courseId ?? undefined,
            lecture_id: filters.lectureId ?? undefined,
            note_type: filters.noteType ?? undefined,
            q: filters.q || undefined,
            roots_only: filters.rootsOnly ?? undefined,
            limit: filters.limit ?? 30,
            offset: filters.offset ?? 0,
          },
        })
      ).data,
    // Keep the previous page on screen while the next one loads.
    placeholderData: (previous) => previous,
  });
}

export function useNote(noteId: number | null) {
  return useQuery<NoteDetail>({
    queryKey: ["note", noteId],
    queryFn: async () => (await api.get(`/notes/${noteId}`)).data,
    enabled: noteId !== null && Number.isFinite(noteId),
  });
}

export function useNoteVersions(noteId: number | null, enabled = true) {
  return useQuery<NoteVersions>({
    queryKey: ["noteVersions", noteId],
    queryFn: async () => (await api.get(`/notes/${noteId}/versions`)).data,
    enabled: enabled && noteId !== null && Number.isFinite(noteId),
  });
}

export function useNoteDiff(noteId: number | null, against: number | null) {
  return useQuery<NoteDiff>({
    queryKey: ["noteDiff", noteId, against],
    queryFn: async () =>
      (await api.get(`/notes/${noteId}/diff`, { params: { against } })).data,
    enabled: !!noteId && !!against && noteId !== against,
  });
}

function useNoteInvalidation() {
  const queryClient = useQueryClient();
  return useCallback(
    (noteId?: number) => {
      queryClient.invalidateQueries({ queryKey: notesKey });
      queryClient.invalidateQueries({ queryKey: ["dashboardSummary"] });
      queryClient.invalidateQueries({ queryKey: ["courses"] });
      if (noteId) {
        queryClient.invalidateQueries({ queryKey: ["note", noteId] });
        queryClient.invalidateQueries({ queryKey: ["noteVersions", noteId] });
      }
    },
    [queryClient],
  );
}

export function useGenerate() {
  const invalidate = useNoteInvalidation();
  return useMutation<GenerateResponse, unknown, GenerateArgs>({
    mutationFn: async (args) => (await api.post("/notes/generate", args)).data,
    onSuccess: () => invalidate(),
  });
}

export function useRefine() {
  const invalidate = useNoteInvalidation();
  return useMutation<
    GenerateResponse,
    unknown,
    { noteId: number; instruction: string; selection?: string }
  >({
    mutationFn: async ({ noteId, instruction, selection }) =>
      (await api.post(`/notes/${noteId}/refine`, { instruction, selection })).data,
    onSuccess: (_data, variables) => invalidate(variables.noteId),
  });
}

/** Save the user's own version. Teaching the style profile is opt-out, not implicit. */
export function useSaveNote() {
  const invalidate = useNoteInvalidation();
  return useMutation<
    NoteDetail,
    unknown,
    { noteId: number; markdown?: string; title?: string; teach?: boolean }
  >({
    mutationFn: async ({ noteId, markdown, title, teach = true }) =>
      (await api.patch(`/notes/${noteId}`, { markdown, title, teach })).data,
    onSuccess: (_data, variables) => invalidate(variables.noteId),
  });
}

export function useRevertNote() {
  const invalidate = useNoteInvalidation();
  return useMutation<NoteDetail, unknown, number>({
    mutationFn: async (noteId) => (await api.post(`/notes/${noteId}/revert`)).data,
    onSuccess: (_data, noteId) => invalidate(noteId),
  });
}

export function useDeleteNote() {
  const invalidate = useNoteInvalidation();
  return useMutation<void, unknown, number>({
    mutationFn: async (noteId) => {
      await api.delete(`/notes/${noteId}`);
    },
    onSuccess: () => invalidate(),
  });
}

export function useFeedback() {
  const invalidate = useNoteInvalidation();
  const queryClient = useQueryClient();
  return useMutation<FeedbackResponse, unknown, { noteId: number; edited_markdown: string }>({
    mutationFn: async ({ noteId, edited_markdown }) =>
      (await api.post(`/notes/${noteId}/feedback`, { edited_markdown })).data,
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["styleDashboard"] });
      queryClient.invalidateQueries({ queryKey: ["styleProgress"] });
      invalidate(variables.noteId);
    },
  });
}

export function useSaveAnswer() {
  const invalidate = useNoteInvalidation();
  return useMutation<
    GenerateResponse,
    unknown,
    {
      content: string;
      title?: string;
      lecture_id?: number | null;
      course_id?: number | null;
      append_to_note_id?: number | null;
    }
  >({
    mutationFn: async (payload) => (await api.post("/notes/save-answer", payload)).data,
    onSuccess: (data) => invalidate(data.id),
  });
}

export type StreamStage = "idle" | "retrieving" | "writing" | "saving" | "done" | "error";

/**
 * Streamed generation.
 *
 * Retrieval is reported before the first token, so the wait shows what was
 * found rather than an opaque spinner — and the text appears as it is written
 * instead of arriving all at once after 20 seconds.
 */
export function useStreamingGenerate() {
  const invalidate = useNoteInvalidation();
  const [stage, setStage] = useState<StreamStage>("idle");
  const [text, setText] = useState("");
  const [grounding, setGrounding] = useState<Grounding | null>(null);
  const [noteId, setNoteId] = useState<number | null>(null);
  const [error, setError] = useState<ApiError | Error | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    setStage("idle");
    setText("");
    setGrounding(null);
    setNoteId(null);
    setError(null);
  }, []);

  const cancel = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
    setStage("idle");
  }, []);

  const start = useCallback(
    async (args: GenerateArgs) => {
      reset();
      setStage("retrieving");
      const controller = new AbortController();
      controllerRef.current = controller;

      try {
        await streamRequest("/notes/generate/stream", args, {
          signal: controller.signal,
          onEvent: (event, data) => {
            if (event === "retrieval") {
              setGrounding(data as unknown as Grounding);
              setStage("writing");
            } else if (event === "delta") {
              setText((current) => current + String(data.text ?? ""));
              setStage("writing");
            } else if (event === "done") {
              setNoteId(Number(data.id));
              setStage("done");
              invalidate();
            } else if (event === "error") {
              setError(new Error(String(data.message ?? "Generation failed.")));
              setStage("error");
            }
          },
        });
      } catch (streamError) {
        if ((streamError as Error)?.name === "AbortError") return;
        setError(streamError as Error);
        setStage("error");
      } finally {
        controllerRef.current = null;
      }
    },
    [invalidate, reset],
  );

  return {
    start,
    cancel,
    reset,
    stage,
    text,
    grounding,
    noteId,
    error,
    isStreaming: stage === "retrieving" || stage === "writing" || stage === "saving",
  };
}
