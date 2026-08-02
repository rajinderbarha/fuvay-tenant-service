import { useCallback, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../../services/schedule/scheduleApi";
import { AppError } from "../../services/api/types";

function toIso(d: Date): string {
  // Local calendar date, never UTC-shifted (toISOString() can roll the
  // date backward/forward across a timezone boundary near midnight).
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function startOfWeek(d: Date): Date {
  const copy = new Date(d);
  const day = copy.getDay(); // 0=Sunday
  copy.setDate(copy.getDate() - day + 1); // Monday
  return copy;
}

/** Schedule data + guarded mutations (Phase P). Loads a 7-day window
 * anchored to the selected date's week; every mutation refetches rather
 * than mutating the projection locally. */
export function useSchedule(selectedDate: Date) {
  const queryClient = useQueryClient();
  const monday = startOfWeek(selectedDate);
  const sunday = new Date(monday);
  sunday.setDate(sunday.getDate() + 6);
  const from = toIso(monday);
  const to = toIso(sunday);
  const key = ["schedule", from, to] as const;

  const [mutating, setMutating] = useState(false);
  const [mutationError, setMutationError] = useState<AppError | null>(null);

  const query = useQuery({
    queryKey: key,
    queryFn: async ({ signal }) => {
      const result = await api.getSchedule(from, to, signal);
      if (!result.ok) throw result.error;
      return result.data;
    },
  });

  const weekDates = useMemo(() => {
    const dates: Date[] = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(monday);
      d.setDate(d.getDate() + i);
      dates.push(d);
    }
    return dates;
  }, [monday.getTime()]);

  const refresh = useCallback(() => queryClient.invalidateQueries({ queryKey: key }), [queryClient, key]);

  const runMutation = useCallback(async (fn: () => Promise<{ ok: boolean; error?: AppError }>) => {
    if (mutating) return { ok: false as const };
    setMutating(true);
    setMutationError(null);
    try {
      const result = await fn();
      if (!result.ok) {
        setMutationError(result.error ?? null);
        return { ok: false as const, error: result.error };
      }
      await refresh();
      return { ok: true as const };
    } finally {
      setMutating(false);
    }
  }, [mutating, refresh]);

  const addBlockedTime = useCallback((body: { date: string; start_time: string; end_time: string; reason?: string }) =>
    runMutation(() => api.createBlockedTime(body)), [runMutation]);

  const removeBlockedTime = useCallback((blockId: string) =>
    runMutation(() => api.removeBlockedTime(blockId)), [runMutation]);

  const submitTimeOff = useCallback((body: { start_date: string; end_date: string; is_full_day: boolean; start_time?: string; end_time?: string; reason_category: string; note?: string }) =>
    runMutation(() => api.submitTimeOff(body)), [runMutation]);

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error as AppError | null,
    isRefetching: query.isRefetching,
    refetch: query.refetch,
    weekDates,
    mutating, mutationError,
    addBlockedTime, removeBlockedTime, submitTimeOff,
  };
}
