import { useCallback, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../../services/directPayment/directPaymentApi";
import { DirectPaymentMethod } from "../../services/directPayment/types";
import { AppError } from "../../services/api/types";

function queryKey(jobId: string) {
  return ["jobs", "directPayment", jobId] as const;
}

/** Direct Payment Confirmation data + guarded mutations (Phase O). Every
 * mutation discards its own result in favor of a fresh authoritative
 * refetch -- the amount/status shown is always backend-calculated. */
export function useDirectPayment(jobId: string) {
  const queryClient = useQueryClient();
  const key = queryKey(jobId);

  const [mutating, setMutating] = useState(false);
  const [mutationError, setMutationError] = useState<AppError | null>(null);

  const query = useQuery({
    queryKey: key,
    queryFn: async ({ signal }) => {
      const result = await api.getDirectPaymentDetail(jobId, signal);
      if (!result.ok) throw result.error;
      return result.data;
    },
    enabled: Boolean(jobId),
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

  const declarePayment = useCallback((body: { amount: string; method: DirectPaymentMethod; reference_id?: string; note?: string }) =>
    runMutation(() => api.declarePayment(jobId, body)), [runMutation, jobId]);

  const remindCustomer = useCallback(() => runMutation(() => api.remindCustomer(jobId)), [runMutation, jobId]);
  const finalizeJob = useCallback(() => runMutation(() => api.finalizeJob(jobId)), [runMutation, jobId]);

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error as AppError | null,
    isRefetching: query.isRefetching,
    refetch: query.refetch,
    mutating, mutationError,
    declarePayment, remindCustomer, finalizeJob,
  };
}
