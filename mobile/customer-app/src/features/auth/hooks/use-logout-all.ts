import { useCallback, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { authApi } from "../api/auth-api";
import { clearSession, getSessionState } from "../state/session-store";
import { reevaluateStartup } from "../../../app/startup/startup-service";
import { clearRecentSearches } from "../../search/state/recent-search-storage";
import { clearActiveDraftId } from "../../booking-draft/state/draft-local-store";

/** "Sign out of all devices" — CUSTOMER-L5-02 §36. Requires explicit confirmation at the call site (see SessionsScreen). */
export function useLogoutAll() {
  const [loading, setLoading] = useState(false);
  const queryClient = useQueryClient();

  const logoutAll = useCallback(async (): Promise<{ sessionsRevoked: number } | null> => {
    setLoading(true);
    const customerId = getSessionState().session?.userId;
    try {
      const result = await authApi.logoutAll();
      await clearSession();
      queryClient.clear();
      if (customerId) void clearRecentSearches(customerId);
      if (customerId) void clearActiveDraftId(customerId);
      void reevaluateStartup();
      return { sessionsRevoked: result.sessions_revoked };
    } catch {
      // Server-side revocation failure still gets a local logout — the
      // device this runs on is protected even if other sessions could not
      // be confirmed revoked server-side. See CUSTOMER-L5-02-security-review.md.
      await clearSession();
      queryClient.clear();
      if (customerId) void clearRecentSearches(customerId);
      if (customerId) void clearActiveDraftId(customerId);
      void reevaluateStartup();
      return null;
    } finally {
      setLoading(false);
    }
  }, [queryClient]);

  return { logoutAll, loading };
}
