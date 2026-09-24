import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { DashboardSummary } from "@/lib/types";

export function useDashboardSummary() {
  return useQuery<DashboardSummary>({
    queryKey: ["dashboardSummary"],
    queryFn: async () => (await api.get("/dashboard/summary")).data,
  });
}
