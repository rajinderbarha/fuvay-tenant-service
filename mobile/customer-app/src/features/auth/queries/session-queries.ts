import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { authApi } from "../api/auth-api";
import { parseSessionList } from "../domain/session-summary-schema";
import { queryKeys } from "../../../state/query-client";
import { logger } from "../../../observability/logger";

export const sessionQueryKeys = {
  root: () => queryKeys.all("auth-sessions"),
};

export function useSessions() {
  return useQuery({
    queryKey: sessionQueryKeys.root(),
    queryFn: async () => {
      const response = await authApi.listSessions();
      const { valid, droppedCount } = parseSessionList(response.sessions);
      if (droppedCount > 0) logger.warn("auth.invalid_session_dropped", { droppedCount });
      return valid;
    },
    staleTime: 30_000,
  });
}

export function useRevokeSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) => authApi.revokeSession(sessionId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: sessionQueryKeys.root() });
    },
  });
}
