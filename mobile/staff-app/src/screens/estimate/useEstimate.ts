import { useCallback, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as estimateApi from "../../services/estimate/estimateApi";
import { QuoteItemType } from "../../services/estimate/types";
import { AppError } from "../../services/api/types";

function queryKey(jobId: string) {
  return ["jobs", "estimate", jobId] as const;
}

/**
 * Estimate Builder data + guarded mutations (Phase L). Every mutation
 * discards its own result in favor of a fresh authoritative refetch --
 * totals/status are never computed or advanced client-side.
 */
export function useEstimate(jobId: string) {
  const queryClient = useQueryClient();
  const key = queryKey(jobId);

  const [mutating, setMutating] = useState(false);
  const [mutationError, setMutationError] = useState<AppError | null>(null);

  const query = useQuery({
    queryKey: key,
    queryFn: async ({ signal }) => {
      const result = await estimateApi.getEstimateDetail(jobId, signal);
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

  const createEstimate = useCallback(() => runMutation(() => estimateApi.createEstimate(jobId)), [runMutation, jobId]);

  const createRevision = useCallback((currentQuoteId: string) =>
    runMutation(() => estimateApi.createRevision(jobId, currentQuoteId)), [runMutation, jobId]);

  const addItem = useCallback((quoteId: string, item: { item_type: QuoteItemType; item_name: string; item_description?: string; quantity: number; unit_price: number }) =>
    runMutation(() => estimateApi.addEstimateItem(jobId, quoteId, item)), [runMutation, jobId]);

  const updateItem = useCallback((quoteId: string, itemId: string, patch: { item_name?: string; item_description?: string; quantity?: number; unit_price?: number }) =>
    runMutation(() => estimateApi.updateEstimateItem(jobId, quoteId, itemId, patch)), [runMutation, jobId]);

  const removeItem = useCallback((quoteId: string, itemId: string) =>
    runMutation(() => estimateApi.removeEstimateItem(jobId, quoteId, itemId)), [runMutation, jobId]);

  const sendForApproval = useCallback((quoteId: string, customerNotes?: string) =>
    runMutation(() => estimateApi.sendEstimateForApproval(jobId, quoteId, customerNotes)), [runMutation, jobId]);

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error as AppError | null,
    isRefetching: query.isRefetching,
    refetch: query.refetch,
    mutating, mutationError,
    createEstimate, createRevision, addItem, updateItem, removeItem, sendForApproval,
  };
}
