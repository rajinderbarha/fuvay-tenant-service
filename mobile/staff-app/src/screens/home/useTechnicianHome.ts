import { useCallback, useEffect, useRef } from "react";
import { AppState, AppStateStatus } from "react-native";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "../../navigation/session/SessionProvider";
import { queryKeys } from "../../state/queries/queryKeys";
import * as homeApi from "../../services/home/homeApi";
import { AvailabilityState, MobileHomeDTO } from "../../services/home/types";

const FOREGROUND_REFRESH_THRESHOLD_MS = 30_000;

/**
 * Home screen data + availability mutation (Phase H spec sections 8, 11).
 * A single Home projection request (spec section 11) -- no waterfall of
 * separate calls. Availability updates are optimistic with reliable
 * rollback on failure, and are disabled entirely while the technician
 * isn't in an active/allowed access state.
 */
export function useTechnicianHome() {
  const { accessContext } = useSession();
  const queryClient = useQueryClient();
  const lastForegroundRefetchRef = useRef(0);

  const tenantId = accessContext.tenantId ?? "";
  const technicianId = accessContext.technicianId ?? "";
  const queryKey = queryKeys.technician.home(tenantId, technicianId);

  const query = useQuery({
    queryKey,
    queryFn: async ({ signal }) => {
      const result = await homeApi.getMobileHome(signal);
      if (!result.ok) throw result.error;
      return result.data;
    },
    enabled: Boolean(tenantId && technicianId),
  });

  useEffect(() => {
    const handleAppStateChange = (next: AppStateStatus) => {
      if (next !== "active") return;
      const now = Date.now();
      if (now - lastForegroundRefetchRef.current < FOREGROUND_REFRESH_THRESHOLD_MS) return;
      lastForegroundRefetchRef.current = now;
      query.refetch();
    };
    const sub = AppState.addEventListener("change", handleAppStateChange);
    return () => sub.remove();
  }, [query]);

  const updateAvailability = useCallback(async (nextState: AvailabilityState) => {
    const previous = queryClient.getQueryData<MobileHomeDTO>(queryKey);
    if (!previous) return; // nothing to optimistically update against

    // Optimistic update.
    queryClient.setQueryData<MobileHomeDTO>(queryKey, {
      ...previous,
      availability: { state: nextState, updated_at: new Date().toISOString() },
    });

    const result = await homeApi.updateAvailability(nextState);
    if (!result.ok) {
      // Reliable rollback -- never leave the UI showing an unconfirmed state.
      queryClient.setQueryData<MobileHomeDTO>(queryKey, previous);
      return { ok: false as const, error: result.error };
    }
    queryClient.setQueryData<MobileHomeDTO>(queryKey, current =>
      current ? { ...current, availability: result.data } : current);
    return { ok: true as const };
  }, [queryClient, queryKey]);

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error as { safeMessage?: string } | null,
    isRefetching: query.isRefetching,
    refetch: query.refetch,
    updateAvailability,
    lastUpdatedAt: query.dataUpdatedAt,
  };
}
