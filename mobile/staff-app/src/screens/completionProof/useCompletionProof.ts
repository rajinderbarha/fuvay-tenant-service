import { useCallback, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../../services/completionProof/completionProofApi";
import { uploadChecklistEvidence } from "../../services/media/mediaApi";
import { AppError } from "../../services/api/types";

function queryKey(jobId: string) {
  return ["jobs", "completionProof", jobId] as const;
}

/** Completion Proof data + guarded mutations (Phase N). Every mutation
 * discards its own result in favor of a fresh authoritative refetch. */
export function useCompletionProof(jobId: string) {
  const queryClient = useQueryClient();
  const key = queryKey(jobId);

  const [mutating, setMutating] = useState(false);
  const [mutationError, setMutationError] = useState<AppError | null>(null);
  const [uploadingCategory, setUploadingCategory] = useState<"before" | "after" | null>(null);

  const query = useQuery({
    queryKey: key,
    queryFn: async ({ signal }) => {
      const result = await api.getCompletionProofDetail(jobId, signal);
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

  const saveDraft = useCallback((body: { resolution_summary?: string; final_service_notes?: string }) =>
    runMutation(() => api.saveDraft(jobId, body)), [runMutation, jobId]);

  const removeEvidence = useCallback((category: "before" | "after", fileId: string) =>
    runMutation(() => api.removeEvidence(jobId, category, fileId)), [runMutation, jobId]);

  const addEvidenceFromUpload = useCallback(async (category: "before" | "after", fileUri: string, fileName: string, mimeType: string) => {
    if (uploadingCategory) return { ok: false as const };
    setUploadingCategory(category);
    try {
      const upload = await uploadChecklistEvidence(jobId, fileUri, fileName, mimeType);
      if (!upload.ok) {
        setMutationError(upload.error);
        return { ok: false as const, error: upload.error };
      }
      return await runMutation(() => api.addEvidence(jobId, category, upload.data.id));
    } finally {
      setUploadingCategory(null);
    }
  }, [uploadingCategory, jobId, runMutation]);

  const submit = useCallback(() => runMutation(() => api.submitCompletionProof(jobId)), [runMutation, jobId]);
  const requestHandover = useCallback(() => runMutation(() => api.requestHandover(jobId)), [runMutation, jobId]);
  const sendReminder = useCallback(() => runMutation(() => api.sendHandoverReminder(jobId)), [runMutation, jobId]);
  const markCustomerUnavailable = useCallback(() => runMutation(() => api.markCustomerUnavailable(jobId)), [runMutation, jobId]);

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error as AppError | null,
    isRefetching: query.isRefetching,
    refetch: query.refetch,
    mutating, mutationError, uploadingCategory,
    saveDraft, addEvidenceFromUpload, removeEvidence, submit, requestHandover, sendReminder, markCustomerUnavailable,
  };
}
