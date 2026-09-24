import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { HistoricalSource, StyleDashboard, StyleProgress } from "@/lib/types";

/** Fetches the full style-profile dashboard (profile, sources, versions, progress). */
export function useStyleDashboard() {
  return useQuery<StyleDashboard>({
    queryKey: ["styleDashboard"],
    queryFn: async () => (await api.get("/style/dashboard")).data,
  });
}

export function useStyleProgress() {
  return useQuery<StyleProgress>({
    queryKey: ["styleProgress"],
    queryFn: async () => (await api.get("/style/progress")).data,
  });
}

function useStyleInvalidation() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["styleDashboard"] });
    queryClient.invalidateQueries({ queryKey: ["styleProgress"] });
    queryClient.invalidateQueries({ queryKey: ["dashboardSummary"] });
    queryClient.invalidateQueries({ queryKey: ["stylePreview"] });
  };
}

/** Set one attribute by hand. Pinning holds it against future learning. */
export function useOverrideAttribute() {
  const invalidate = useStyleInvalidation();
  return useMutation<unknown, unknown, { feature: string; value: unknown; pinned?: boolean }>({
    mutationFn: async ({ feature, value, pinned = true }) =>
      (await api.put(`/style/attributes/${feature}`, { value, pinned })).data,
    onSuccess: invalidate,
  });
}

/** Release a hand-set attribute so it is learned again. */
export function useResetAttribute() {
  const invalidate = useStyleInvalidation();
  return useMutation<unknown, unknown, string>({
    mutationFn: async (feature) => (await api.delete(`/style/attributes/${feature}`)).data,
    onSuccess: invalidate,
  });
}

export function useResetProfile() {
  const invalidate = useStyleInvalidation();
  return useMutation({
    mutationFn: async () => (await api.post("/style/reset")).data,
    onSuccess: invalidate,
  });
}

export function useRestoreStyleVersion() {
  const invalidate = useStyleInvalidation();
  return useMutation<unknown, unknown, number>({
    mutationFn: async (version) => (await api.post(`/style/versions/${version}/restore`)).data,
    onSuccess: invalidate,
  });
}

/** A short sample rendered in the current profile — an abstract thing made concrete. */
export function useStylePreview(enabled: boolean) {
  return useQuery<{ markdown: string }>({
    queryKey: ["stylePreview"],
    queryFn: async () => (await api.post("/style/preview")).data,
    enabled,
    staleTime: 60_000,
  });
}

export function useHistoricalSources() {
  return useQuery<HistoricalSource[]>({
    queryKey: ["historicalSources"],
    queryFn: async () => (await api.get("/historical/")).data,
  });
}

export function useImportHistorical() {
  const queryClient = useQueryClient();
  const invalidate = useStyleInvalidation();
  return useMutation<
    { imported_count: number; skipped: string[]; aggregated_features: Record<string, unknown> },
    unknown,
    File[]
  >({
    mutationFn: async (files) => {
      const formData = new FormData();
      files.forEach((file) => formData.append("files", file));
      const { data } = await api.post("/historical/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["historicalSources"] });
      invalidate();
    },
  });
}

export function useDeleteHistorical() {
  const queryClient = useQueryClient();
  const invalidate = useStyleInvalidation();
  return useMutation<void, unknown, number>({
    mutationFn: async (id) => {
      await api.delete(`/historical/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["historicalSources"] });
      invalidate();
    },
  });
}
