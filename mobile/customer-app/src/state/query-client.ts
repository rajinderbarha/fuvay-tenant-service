import { QueryClient, type QueryKey } from "@tanstack/react-query";
import { ApiError } from "../api/api-errors";
import { logger } from "../observability/logger";

/**
 * Query-key factory convention: `[domain, ...qualifiers]`. Keep factories
 * colocated with the feature that owns the data once features start
 * consuming this client — this file only defines the client itself.
 */
export const queryKeys = {
  all: (domain: string) => [domain] as const,
  detail: (domain: string, id: string) => [domain, "detail", id] as const,
  list: (domain: string, filters?: Record<string, unknown>) => [domain, "list", filters ?? {}] as const,
};

function shouldRetry(failureCount: number, error: unknown): boolean {
  if (failureCount >= 2) return false;
  if (error instanceof ApiError) return error.retryable;
  return false;
}

function onQueryError(error: unknown, queryKey: QueryKey) {
  logger.warn("query.error", { queryKey: JSON.stringify(queryKey), category: error instanceof ApiError ? error.category : "unknown_error" });
}

// Created once at module scope — never inside a component render — so
// identity is stable across the app's lifetime.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      retry: shouldRetry,
      refetchOnWindowFocus: false, // no window-focus concept on native; refetchOnReconnect covers connectivity recovery
      refetchOnReconnect: true,
      networkMode: "online",
    },
    mutations: {
      // Mutations are never auto-retried — retrying an unsafe write silently is prohibited by this sprint's API contract.
      retry: false,
      networkMode: "online",
      onError: (error) => logger.warn("mutation.error", { category: error instanceof ApiError ? error.category : "unknown_error" }),
    },
  },
});

queryClient.getQueryCache().subscribe((event) => {
  if (event.type === "updated" && event.query.state.status === "error") {
    onQueryError(event.query.state.error, event.query.queryKey);
  }
});
