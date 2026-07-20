import { useCallback, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { authApi } from "../api/auth-api";
import { clearSession, getSessionState } from "../state/session-store";
import { reevaluateStartup } from "../../../app/startup/startup-service";
import { clearRecentSearches } from "../../search/state/recent-search-storage";
import { clearActiveDraftId } from "../../booking-draft/state/draft-local-store";

export function useLogout() {
  const [loading, setLoading] = useState(false);
  const queryClient = useQueryClient();

  const logout = useCallback(async () => {
    setLoading(true);
    const customerId = getSessionState().session?.userId;
    try {
      await authApi.logout();
    } catch {
      // Server-side revocation failure must not block a local logout —
      // clearing the local session is what actually protects the device.
    } finally {
      await clearSession();
      // Every server-state query this app has (profile, sessions, and any
      // future customer-specific data) is cleared here — an account switch
      // must never show a flash of the previous customer's cached data
      // (CUSTOMER-L5-02 §42/§50).
      queryClient.clear();
      // Recent searches are local-only (CUSTOMER-L5-04 §22) and must not
      // survive an account switch on a shared device either.
      if (customerId) void clearRecentSearches(customerId);
      // The active booking-draft ID is only a pointer, but it must not
      // survive an account switch either — restoring it for a new customer
      // could otherwise resume the previous customer's booking flow
      // (CUSTOMER-L5-06 §49).
      if (customerId) void clearActiveDraftId(customerId);
      void reevaluateStartup();
      setLoading(false);
    }
  }, [queryClient]);

  return { logout, loading };
}
