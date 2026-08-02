import { useCallback, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as workExecutionApi from "../../services/workExecution/workExecutionApi";
import { AppError } from "../../services/api/types";

function queryKey(jobId: string) {
  return ["jobs", "workExecution", jobId] as const;
}

/**
 * Work Execution data + guarded mutations (Phase M). Every mutation
 * discards its own result in favor of a fresh authoritative refetch --
 * session state/readiness are never advanced client-side.
 */
export function useWorkExecution(jobId: string) {
  const queryClient = useQueryClient();
  const key = queryKey(jobId);

  const [mutating, setMutating] = useState(false);
  const [mutationError, setMutationError] = useState<AppError | null>(null);

  const query = useQuery({
    queryKey: key,
    queryFn: async ({ signal }) => {
      const result = await workExecutionApi.getWorkExecutionDetail(jobId, signal);
      if (!result.ok) throw result.error;
      return result.data;
    },
    enabled: Boolean(jobId),
    refetchInterval: (q) => (q.state.data?.work_session?.state === "active" ? 30000 : false),
  });

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

  const startWork = useCallback(() => runMutation(() => workExecutionApi.startWork(jobId)), [runMutation, jobId]);
  const pauseWork = useCallback((reason?: string) => runMutation(() => workExecutionApi.pauseWork(jobId, reason)), [runMutation, jobId]);
  const resumeWork = useCallback(() => runMutation(() => workExecutionApi.resumeWork(jobId)), [runMutation, jobId]);
  const finishWork = useCallback(() => runMutation(() => workExecutionApi.finishWork(jobId)), [runMutation, jobId]);

  const requestPart = useCallback((body: { part_name: string; quantity: number; estimated_cost: number; reason: string; technician_note?: string }) =>
    runMutation(() => workExecutionApi.createPartsRequest(jobId, body)), [runMutation, jobId]);

  const saveChecklistResponse = useCallback((instanceId: string, itemId: string, value: Record<string, unknown> | null, evidence: { file_id: string }[] | null) =>
    runMutation(() => workExecutionApi.saveWorkChecklistResponse(instanceId, itemId, value, evidence)), [runMutation]);

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error as AppError | null,
    isRefetching: query.isRefetching,
    refetch: query.refetch,
    mutating, mutationError,
    startWork, pauseWork, resumeWork, finishWork, requestPart, saveChecklistResponse,
  };
}
