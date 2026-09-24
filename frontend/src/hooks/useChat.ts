import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";

import api from "@/lib/api";
import { streamRequest } from "@/lib/sse";
import type { ChatThreadDetail, ChatThreadSummary, Citation, Scope } from "@/lib/types";

export interface ChatScope {
  scope: Scope;
  course_id?: number | null;
  lecture_id?: number | null;
  note_id?: number | null;
}

export function useChatThreads(filters: Partial<ChatScope> = {}) {
  return useQuery<ChatThreadSummary[]>({
    queryKey: ["chatThreads", filters],
    queryFn: async () =>
      (
        await api.get("/chat/threads", {
          params: {
            scope: filters.scope,
            course_id: filters.course_id ?? undefined,
            lecture_id: filters.lecture_id ?? undefined,
            note_id: filters.note_id ?? undefined,
          },
        })
      ).data,
  });
}

export function useChatThread(threadId: number | null) {
  return useQuery<ChatThreadDetail>({
    queryKey: ["chatThread", threadId],
    queryFn: async () => (await api.get(`/chat/threads/${threadId}`)).data,
    enabled: threadId !== null && Number.isFinite(threadId),
  });
}

export function useChatSuggestions(params: { noteId?: number | null; lectureId?: number | null }) {
  return useQuery<string[]>({
    queryKey: ["chatSuggestions", params],
    queryFn: async () =>
      (
        await api.get("/chat/suggestions", {
          params: { note_id: params.noteId ?? undefined, lecture_id: params.lectureId ?? undefined },
        })
      ).data,
  });
}

export function useDeleteThread() {
  const queryClient = useQueryClient();
  return useMutation<void, unknown, number>({
    mutationFn: async (threadId) => {
      await api.delete(`/chat/threads/${threadId}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["chatThreads"] }),
  });
}

export interface LocalMessage {
  id: string | number;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  pending?: boolean;
}

/**
 * A streamed conversation scoped to a note, lecture or course.
 *
 * Citations arrive as soon as retrieval resolves — before the answer is
 * written — so the sources are visible while the model is still talking.
 */
export function useChat(scope: ChatScope) {
  const queryClient = useQueryClient();
  const [threadId, setThreadId] = useState<number | null>(null);
  const [messages, setMessages] = useState<LocalMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  const loadThread = useCallback(async (id: number) => {
    setThreadId(id);
    const { data } = await api.get<ChatThreadDetail>(`/chat/threads/${id}`);
    setMessages(
      data.messages.map((m) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        citations: m.citations ?? [],
      })),
    );
  }, []);

  const startNew = useCallback(() => {
    controllerRef.current?.abort();
    setThreadId(null);
    setMessages([]);
    setError(null);
    setIsStreaming(false);
  }, []);

  const send = useCallback(
    async (question: string) => {
      const text = question.trim();
      if (!text || isStreaming) return;

      setError(null);
      setIsStreaming(true);
      const pendingId = `pending-${Date.now()}`;
      setMessages((current) => [
        ...current,
        { id: `user-${Date.now()}`, role: "user", content: text, citations: [] },
        { id: pendingId, role: "assistant", content: "", citations: [], pending: true },
      ]);

      const controller = new AbortController();
      controllerRef.current = controller;

      const patchPending = (patch: Partial<LocalMessage>) =>
        setMessages((current) =>
          current.map((m) => (m.id === pendingId ? { ...m, ...patch } : m)),
        );

      try {
        await streamRequest(
          "/chat/stream",
          { message: text, thread_id: threadId, ...scope },
          {
            signal: controller.signal,
            onEvent: (event, data) => {
              if (event === "thread") {
                setThreadId(Number(data.thread_id));
              } else if (event === "citations") {
                patchPending({ citations: (data.citations as Citation[]) ?? [] });
              } else if (event === "delta") {
                setMessages((current) =>
                  current.map((m) =>
                    m.id === pendingId
                      ? { ...m, content: m.content + String(data.text ?? "") }
                      : m,
                  ),
                );
              } else if (event === "done") {
                patchPending({ id: Number(data.message_id), pending: false });
                queryClient.invalidateQueries({ queryKey: ["chatThreads"] });
              } else if (event === "error") {
                setError(new Error(String(data.message ?? "The answer failed.")));
                patchPending({ pending: false });
              }
            },
          },
        );
      } catch (streamError) {
        if ((streamError as Error)?.name !== "AbortError") {
          setError(streamError as Error);
        }
        // Drop the empty placeholder so a failure doesn't leave a blank bubble.
        setMessages((current) =>
          current.filter((m) => !(m.id === pendingId && !m.content.trim())),
        );
      } finally {
        patchPending({ pending: false });
        setIsStreaming(false);
        controllerRef.current = null;
      }
    },
    [isStreaming, queryClient, scope, threadId],
  );

  const stop = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
    setIsStreaming(false);
  }, []);

  return { threadId, messages, send, stop, startNew, loadThread, isStreaming, error };
}
