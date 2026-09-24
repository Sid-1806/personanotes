"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

import { ToastProvider } from "@/components/ui/Toast";
import { ApiError } from "@/lib/api";

export default function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            refetchOnWindowFocus: false,
            // Retrying a 401/403/404 just delays the real answer; retry the
            // failures that are actually transient.
            retry: (failureCount, error) => {
              if (error instanceof ApiError) {
                if (["unauthorized", "not_found", "validation", "rate_limited"].includes(error.kind)) {
                  return false;
                }
              }
              return failureCount < 2;
            },
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>{children}</ToastProvider>
    </QueryClientProvider>
  );
}
