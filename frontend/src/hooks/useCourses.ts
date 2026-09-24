import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Course } from "@/lib/types";

export const coursesKey = ["courses"] as const;

export function useCourses(includeArchived = false) {
  return useQuery<Course[]>({
    queryKey: [...coursesKey, { includeArchived }],
    queryFn: async () =>
      (await api.get("/courses/", { params: { include_archived: includeArchived } })).data,
  });
}

export function useCourse(courseId: number | null) {
  return useQuery<Course>({
    queryKey: ["course", courseId],
    queryFn: async () => (await api.get(`/courses/${courseId}`)).data,
    enabled: courseId !== null && Number.isFinite(courseId),
  });
}

function useCourseInvalidation() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: coursesKey });
    queryClient.invalidateQueries({ queryKey: ["dashboardSummary"] });
  };
}

export function useCreateCourse() {
  const invalidate = useCourseInvalidation();
  return useMutation<Course, unknown, { name: string; code?: string; color?: string }>({
    mutationFn: async (payload) => (await api.post("/courses/", payload)).data,
    onSuccess: invalidate,
  });
}

export function useUpdateCourse() {
  const queryClient = useQueryClient();
  const invalidate = useCourseInvalidation();
  return useMutation<
    Course,
    unknown,
    { id: number; name?: string; code?: string; color?: string; archived?: boolean }
  >({
    mutationFn: async ({ id, ...payload }) => (await api.patch(`/courses/${id}`, payload)).data,
    onSuccess: (course) => {
      queryClient.invalidateQueries({ queryKey: ["course", course.id] });
      invalidate();
    },
  });
}

export function useDeleteCourse() {
  const invalidate = useCourseInvalidation();
  const queryClient = useQueryClient();
  return useMutation<void, unknown, number>({
    mutationFn: async (id) => {
      await api.delete(`/courses/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lectures"] });
      queryClient.invalidateQueries({ queryKey: ["notes"] });
      invalidate();
    },
  });
}
