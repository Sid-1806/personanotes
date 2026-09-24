import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Lecture, LectureText, NoteSummary } from "@/lib/types";

export const lecturesKey = ["lectures"] as const;

interface LectureFilters {
  courseId?: number | null;
}

export function useLectures({ courseId }: LectureFilters = {}) {
  const queryClient = useQueryClient();

  const lecturesQuery = useQuery<Lecture[]>({
    queryKey: [...lecturesKey, { courseId: courseId ?? null }],
    queryFn: async () =>
      (
        await api.get("/lectures/", {
          params: courseId ? { course_id: courseId } : undefined,
        })
      ).data,
    // Poll while anything is still being processed, so the UI reflects the
    // pending -> processing -> ready | failed pipeline live.
    refetchInterval: (query) => {
      const data = query.state.data;
      const active =
        Array.isArray(data) &&
        data.some((l) => l.ingestion_status === "pending" || l.ingestion_status === "processing");
      return active ? 3000 : false;
    },
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: lecturesKey });
    queryClient.invalidateQueries({ queryKey: ["courses"] });
    queryClient.invalidateQueries({ queryKey: ["dashboardSummary"] });
  };

  const uploadMutation = useMutation<Lecture[], unknown, { files: File[]; courseId?: number | null }>({
    mutationFn: async ({ files, courseId: target }) => {
      const formData = new FormData();
      files.forEach((file) => formData.append("files", file));
      const { data } = await api.post("/lectures/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        params: target ? { course_id: target } : undefined,
      });
      return data;
    },
    onSuccess: invalidate,
  });

  const retryMutation = useMutation<Lecture, unknown, number>({
    mutationFn: async (id) => (await api.post(`/lectures/${id}/retry`)).data,
    onSuccess: invalidate,
  });

  const updateMutation = useMutation<
    Lecture,
    unknown,
    { id: number; title?: string; course_id?: number }
  >({
    mutationFn: async ({ id, ...payload }) => (await api.patch(`/lectures/${id}`, payload)).data,
    onSuccess: invalidate,
  });

  const deleteMutation = useMutation<void, unknown, { id: number; keepNotes?: boolean }>({
    mutationFn: async ({ id, keepNotes = true }) => {
      await api.delete(`/lectures/${id}`, { params: { keep_notes: keepNotes } });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notes"] });
      invalidate();
    },
  });

  return {
    lectures: lecturesQuery.data ?? [],
    isLoading: lecturesQuery.isLoading,
    isError: lecturesQuery.isError,
    error: lecturesQuery.error,
    upload: uploadMutation,
    retry: retryMutation,
    update: updateMutation,
    remove: deleteMutation,
  };
}

export function useLecture(lectureId: number | null) {
  return useQuery<Lecture>({
    queryKey: ["lecture", lectureId],
    queryFn: async () => (await api.get(`/lectures/${lectureId}`)).data,
    enabled: lectureId !== null && Number.isFinite(lectureId),
    refetchInterval: (query) => {
      const status = query.state.data?.ingestion_status;
      return status === "pending" || status === "processing" ? 3000 : false;
    },
  });
}

export function useLectureNotes(lectureId: number | null) {
  return useQuery<NoteSummary[]>({
    queryKey: ["lectureNotes", lectureId],
    queryFn: async () => (await api.get(`/lectures/${lectureId}/notes`)).data,
    enabled: lectureId !== null && Number.isFinite(lectureId),
  });
}

/** Extracted text, so a bad parse can be diagnosed rather than guessed at. */
export function useLectureText(lectureId: number | null, enabled: boolean) {
  return useQuery<LectureText>({
    queryKey: ["lectureText", lectureId],
    queryFn: async () => (await api.get(`/lectures/${lectureId}/text`)).data,
    enabled: enabled && lectureId !== null && Number.isFinite(lectureId),
  });
}
