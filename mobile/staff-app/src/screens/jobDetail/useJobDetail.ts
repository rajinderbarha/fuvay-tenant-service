import { useCallback, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "../../navigation/session/SessionProvider";
import { queryKeys } from "../../state/queries/queryKeys";
import * as jobDetailApi from "../../services/jobDetail/jobDetailApi";
import { AppError } from "../../services/api/types";

/**
 * Job Detail data + guarded simple mutations (Phase J spec sections 8, 17).
 * Never advances workflow optimistically -- every mutation result is
 * discarded in favor of a fresh authoritative refetch (spec: "Never
 * perform optimistic workflow advancement").
 */
export function useJobDetail(jobId: string) {
  const { accessContext } = useSession();
  const queryClient = useQueryClient();
  const tenantId = accessContext.tenantId ?? "";
  const technicianId = accessContext.technicianId ?? "";
  const queryKey = queryKeys.jobs.detail(tenantId, technicianId, jobId);

  const [mutating, setMutating] = useState(false);
  const [mutationError, setMutationError] = useState<AppError | null>(null);

  const query = useQuery({
    queryKey,
    queryFn: async ({ signal }) => {
      const result = await jobDetailApi.getJobDetail(jobId, signal);
      if (!result.ok) throw result.error;
      return result.data;
    },
    enabled: Boolean(tenantId && technicianId && jobId),
  });

  const runMutation = useCallback(async (mutationFn: () => ReturnType<typeof jobDetailApi.startTravel>) => {
    if (mutating) return; // duplicate-submission guard (spec section 8)
    setMutating(true);
    setMutationError(null);
    try {
      const result = await mutationFn();
      if (!result.ok) {
        setMutationError(result.error);
        return { ok: false as const, error: result.error };
      }
      // Never optimistic -- always re-fetch authoritative state after success.
      await queryClient.invalidateQueries({ queryKey });
      return { ok: true as const };
    } finally {
      setMutating(false);
    }
  }, [mutating, queryClient, queryKey]);

  const acceptJob = useCallback(() => runMutation(() => jobDetailApi.acceptJob(jobId)), [runMutation, jobId]);
  const startTravel = useCallback(() => runMutation(() => jobDetailApi.startTravel(jobId)), [runMutation, jobId]);
  const markArrived = useCallback(() => runMutation(() => jobDetailApi.markArrived(jobId)), [runMutation, jobId]);

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error as AppError | null,
    isRefetching: query.isRefetching,
    refetch: query.refetch,
    mutating,
    mutationError,
    acceptJob,
    startTravel,
    markArrived,
  };
}
