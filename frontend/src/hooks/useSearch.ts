import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { JumpMatch, SearchResults } from "@/lib/types";

export interface SearchParams {
  q: string;
  scope?: "all" | "lectures" | "notes";
  courseId?: number | null;
  lectureId?: number | null;
}

export function useSearch({ q, scope = "all", courseId, lectureId }: SearchParams) {
  const query = q.trim();
  return useQuery<SearchResults>({
    queryKey: ["search", query, scope, courseId ?? null, lectureId ?? null],
    queryFn: async () =>
      (
        await api.get("/search/", {
          params: {
            q: query,
            scope,
            course_id: courseId ?? undefined,
            lecture_id: lectureId ?? undefined,
          },
        })
      ).data,
    enabled: query.length > 1,
    // Keep the previous results visible while the next query resolves, so the
    // page doesn't flash empty on every keystroke.
    placeholderData: (previous) => previous,
  });
}

/** Title-only matches for the command palette. */
export function useJump(q: string) {
  const query = q.trim();
  return useQuery<JumpMatch[]>({
    queryKey: ["jump", query],
    queryFn: async () => (await api.get("/search/jump", { params: { q: query } })).data,
    enabled: query.length > 0,
    placeholderData: (previous) => previous,
  });
}
