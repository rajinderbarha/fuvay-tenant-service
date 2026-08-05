import { QueryClient } from "@tanstack/react-query";

/**
 * One canonical server-state/query-cache client. Defaults: short stale
 * time so customer-facing state (bookings, quotes, invoices) stays fresh,
 * no retry on 4xx (permission/validation errors won't fix themselves), and
 * mutations never retry automatically -- a retried mutation could
 * double-submit a booking or payment-adjacent action.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      retry: (failureCount, error) => {
        const status = (error as { status?: number } | undefined)?.status;
        if (status && status >= 400 && status < 500) return false;
        return failureCount < 2;
      },
      refetchOnReconnect: true,
    },
    mutations: {
      retry: false,
    },
  },
});
