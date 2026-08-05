import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { listMySessions, revokeSession, revokeOtherSessions } from "./customerSecurityApi";
import { adaptCustomerSession } from "../adapters/customerSecurity";

/** Shared session query key -- reused by Security's "This device" preview
 * and this screen's full list/revoke mutations (spec section 16: one
 * source of truth, never a second copy). */
export const SESSIONS_QUERY_KEY = ["customer", "security", "sessions"] as const;

export function useCustomerSessionsQuery() {
  return useQuery({
    queryKey: SESSIONS_QUERY_KEY,
    queryFn: async () => {
      const res = await listMySessions();
      return res.data.sessions.map(adaptCustomerSession);
    },
  });
}

export function useRevokeSessionMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) => revokeSession(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SESSIONS_QUERY_KEY });
    },
  });
}

/** Preserves the current session server-side (spec section 10) -- only
 * the sessions list/count is invalidated, never the broader customer
 * cache (spec section 16: a revoke-other-sessions call must not clear
 * unrelated application data). */
export function useRevokeOtherSessionsMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => revokeOtherSessions(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SESSIONS_QUERY_KEY });
    },
  });
}
