import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../../services/auth/securityApi";
import { AppError } from "../../services/api/types";

const QUERY_KEY = ["security-summary"] as const;

/** Security & MFA hub (Phase V). Every fact on screen is backend-derived
 * from the real security-overview/session/activity projections -- never a
 * client-calculated "Protected" state. */
export function useSecurity() {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: QUERY_KEY,
    queryFn: async ({ signal }) => {
      const result = await api.getSecuritySummary(signal);
      if (!result.ok) throw result.error;
      return result.data;
    },
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error as AppError | null,
    isRefetching: query.isRefetching,
    refetch: query.refetch,
    invalidate: () => queryClient.invalidateQueries({ queryKey: QUERY_KEY }),
  };
}
