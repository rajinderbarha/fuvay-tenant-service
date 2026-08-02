import { useCallback, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../../services/notifications/preferencesApi";
import { AppError } from "../../services/api/types";

const QUERY_KEY = ["staff-notification-preferences"] as const;

type SaveStatus = "idle" | "saving" | "saved" | "error";

/**
 * Notification Preferences (Phase U). Toggles update the visible state only
 * after the backend mutation SUCCEEDS -- never claims "Saved" before that
 * (spec section 2, 9). A version mismatch (spec section 13) reloads
 * authoritative data instead of silently overwriting a changed policy.
 */
export function useNotificationPreferences() {
  const queryClient = useQueryClient();
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [saveError, setSaveError] = useState<AppError | null>(null);
  const [versionConflict, setVersionConflict] = useState(false);
  // Serializes rapid repeated toggles so an older response can never
  // overwrite a newer choice (spec section 9).
  const mutationChain = useRef(Promise.resolve());

  const query = useQuery({
    queryKey: QUERY_KEY,
    queryFn: async ({ signal }) => {
      const result = await api.getNotificationPreferences(signal);
      if (!result.ok) throw result.error;
      return result.data;
    },
  });

  const runMutation = useCallback((task: () => Promise<{ ok: boolean; error?: AppError }>) => {
    const chained = mutationChain.current.then(async () => {
      setSaveStatus("saving");
      setSaveError(null);
      setVersionConflict(false);
      const result = await task();
      if (result.ok) {
        setSaveStatus("saved");
      } else {
        setSaveStatus("error");
        if (result.error) {
          setSaveError(result.error);
          if (result.error.code === "CONFLICT") {
            setVersionConflict(true);
            await queryClient.invalidateQueries({ queryKey: QUERY_KEY });
          }
        }
      }
    });
    mutationChain.current = chained;
    return chained;
  }, [queryClient]);

  const toggleEvent = useCallback((code: string, enabled: boolean) => {
    if (!query.data) return;
    const version = query.data.version;
    // Optimistic update -- safe here because a locked/mandatory toggle never
    // reaches this call (the UI disables it), and failure paths below
    // invalidate to restore authoritative state (the rollback).
    queryClient.setQueryData(QUERY_KEY, (prev: typeof query.data | undefined) => prev ? {
      ...prev, events: prev.events.map(e => e.code === code ? { ...e, push_enabled: enabled } : e),
    } : prev);

    return runMutation(async () => {
      const result = await api.updateEventPreference(code, enabled, version);
      if (result.ok) {
        queryClient.setQueryData(QUERY_KEY, result.data);
        return { ok: true };
      }
      // Rollback: authoritative refetch replaces the optimistic guess.
      await queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      return { ok: false, error: result.error };
    });
  }, [query.data, queryClient, runMutation]);

  const saveQuietHours = useCallback((enabled: boolean, startLocalTime: string | null, endLocalTime: string | null) => {
    if (!query.data) return Promise.resolve();
    const version = query.data.version;
    return runMutation(async () => {
      const result = await api.updateQuietHours({ enabled, startLocalTime, endLocalTime, version });
      if (result.ok) {
        queryClient.setQueryData(QUERY_KEY, result.data);
        return { ok: true };
      }
      return { ok: false, error: result.error };
    });
  }, [query.data, queryClient, runMutation]);

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error as AppError | null,
    isRefetching: query.isRefetching,
    refetch: query.refetch,
    saveStatus, saveError, versionConflict,
    toggleEvent, saveQuietHours,
  };
}
